#include "maestro/Agent.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace {

constexpr double kTwoPi = 2.0 * 3.14159265358979323846;

struct EnvelopeTimes {
    double attackSeconds;
    double decaySeconds;
    double sustainLevel;
    double releaseSeconds;
};

EnvelopeTimes envelopeForRole(maestro::Role role) {
    switch (role) {
    case maestro::Role::Melody:
        return {0.01, 0.08, 0.72, 0.10};
    case maestro::Role::Pad:
        return {0.30, 0.25, 0.78, 0.55};
    case maestro::Role::Bass:
        return {0.015, 0.10, 0.82, 0.12};
    case maestro::Role::Chords:
        return {0.04, 0.18, 0.70, 0.22};
    case maestro::Role::Drums:
        return {0.002, 0.06, 0.35, 0.08};
    }
    return {0.02, 0.12, 0.70, 0.15};
}

double envelopeAt(std::size_t frame, std::size_t frameCount, int sampleRate,
                  const EnvelopeTimes& envelope) {
    const std::size_t attackFrames = static_cast<std::size_t>(
        envelope.attackSeconds * static_cast<double>(sampleRate));
    const std::size_t decayFrames = static_cast<std::size_t>(
        envelope.decaySeconds * static_cast<double>(sampleRate));
    const std::size_t releaseFrames = static_cast<std::size_t>(
        envelope.releaseSeconds * static_cast<double>(sampleRate));

    if (attackFrames > 0U && frame < attackFrames) {
        return static_cast<double>(frame) / static_cast<double>(attackFrames);
    }
    if (decayFrames > 0U && frame < attackFrames + decayFrames) {
        const double progress = static_cast<double>(frame - attackFrames) /
                                static_cast<double>(decayFrames);
        return 1.0 + (envelope.sustainLevel - 1.0) * progress;
    }
    if (releaseFrames > 0U && frameCount > releaseFrames &&
        frame >= frameCount - releaseFrames) {
        const double progress = static_cast<double>(frame - (frameCount - releaseFrames)) /
                                static_cast<double>(releaseFrames);
        return envelope.sustainLevel * (1.0 - progress);
    }
    return envelope.sustainLevel;
}

double oscillatorAt(maestro::Osc oscillator, double phase) {
    const double cycle = phase / kTwoPi;
    switch (oscillator) {
    case maestro::Osc::Sine:
        return std::sin(phase);
    case maestro::Osc::Square:
        return std::sin(phase) >= 0.0 ? 1.0 : -1.0;
    case maestro::Osc::Saw:
        return 2.0 * cycle - 1.0;
    case maestro::Osc::Triangle:
        return 1.0 - 4.0 * std::abs(cycle - 0.5);
    case maestro::Osc::Noise:
        return std::sin(phase);
    }
    return 0.0;
}

enum class DrumVoice { Kick, Snare, Hat };

DrumVoice drumVoiceForPitch(int pitchMidi) {
    if (pitchMidi <= 36) {
        return DrumVoice::Kick;
    }
    if (pitchMidi <= 40) {
        return DrumVoice::Snare;
    }
    return DrumVoice::Hat;
}

double deterministicNoise(std::size_t localFrame, std::size_t startFrame, int pitchMidi) {
    std::uint64_t value = static_cast<std::uint64_t>(localFrame) +
                          (static_cast<std::uint64_t>(startFrame) << 1U) +
                          (static_cast<std::uint64_t>(pitchMidi) << 33U) +
                          0x9e3779b97f4a7c15ULL;
    value ^= value >> 30U;
    value *= 0xbf58476d1ce4e5b9ULL;
    value ^= value >> 27U;
    value *= 0x94d049bb133111ebULL;
    value ^= value >> 31U;
    return static_cast<double>(value >> 11U) * (1.0 / 9007199254740992.0) * 2.0 - 1.0;
}

double drumSampleAt(DrumVoice voice, std::size_t localFrame, std::size_t startFrame,
                    int pitchMidi, int sampleRate) {
    const double time = static_cast<double>(localFrame) / static_cast<double>(sampleRate);
    const double noise = deterministicNoise(localFrame, startFrame, pitchMidi);

    switch (voice) {
    case DrumVoice::Kick: {
        const double envelope = std::exp(-time * 15.0);
        const double frequencyHz = 48.0 + 112.0 * std::exp(-time * 24.0);
        const double phase = kTwoPi * frequencyHz * time;
        const double click = 0.16 * noise * std::exp(-time * 95.0);
        return (std::sin(phase) * envelope) + click;
    }
    case DrumVoice::Snare: {
        const double envelope = std::exp(-time * 22.0);
        const double tone = std::sin(kTwoPi * 190.0 * time) * std::exp(-time * 34.0);
        return (0.82 * noise + 0.18 * tone) * envelope;
    }
    case DrumVoice::Hat: {
        const double envelope = std::exp(-time * 58.0);
        const double previousNoise = localFrame == 0U
            ? 0.0
            : deterministicNoise(localFrame - 1U, startFrame, pitchMidi);
        return (noise - previousNoise) * envelope;
    }
    }
    return 0.0;
}

const maestro::Track* findTrack(const maestro::Score& score, int trackId) {
    for (const maestro::Track& track : score.tracks) {
        if (track.id == trackId) {
            return &track;
        }
    }
    return nullptr;
}

}  // namespace

namespace maestro {

AudioBuffer renderSineTone(double frequencyHz, double seconds, int sampleRate) {
    const int outputSampleRate = sampleRate > 0 ? sampleRate : 44100;
    AudioBuffer audio;
    audio.sampleRate = outputSampleRate;
    audio.channels = 1;

    if (!std::isfinite(frequencyHz) || !std::isfinite(seconds) ||
        frequencyHz <= 0.0 || seconds <= 0.0) {
        return audio;
    }

    const double frameCountDouble = seconds * static_cast<double>(outputSampleRate);
    if (!std::isfinite(frameCountDouble) || frameCountDouble >
            static_cast<double>(std::numeric_limits<std::size_t>::max())) {
        return audio;
    }

    const std::size_t frameCount = static_cast<std::size_t>(frameCountDouble);
    if (frameCount == 0U || frameCount > audio.samples.max_size()) {
        return audio;
    }

    audio.samples.resize(frameCount);
    const double twoPi = 2.0 * std::acos(-1.0);
    const double phaseStep = twoPi * std::fmod(frequencyHz,
                                                static_cast<double>(outputSampleRate)) /
                             static_cast<double>(outputSampleRate);
    double phase = 0.0;
    for (std::size_t frame = 0; frame < frameCount; ++frame) {
        audio.samples[frame] = static_cast<float>(std::sin(phase));
        phase += phaseStep;
        if (phase >= twoPi) {
            phase -= twoPi;
        }
    }

    return audio;
}

void synthesize(Blackboard& bb) {
    const Score& score = bb.score;
    AudioBuffer audio;
    audio.sampleRate = score.ctx.sampleRate;
    audio.channels = 1;

    const int sampleRate = score.ctx.sampleRate;
    const int tempoBpm = score.ctx.tempoBpm;
    if (sampleRate <= 0 || tempoBpm <= 0 || !std::isfinite(score.lengthBeats) ||
        score.lengthBeats <= 0.0) {
        bb.audio = std::move(audio);
        return;
    }

    const double secondsPerBeat = 60.0 / static_cast<double>(tempoBpm);
    const double totalFramesDouble = score.lengthBeats * secondsPerBeat *
                                    static_cast<double>(sampleRate);
    if (!std::isfinite(totalFramesDouble) || totalFramesDouble <= 0.0 ||
        totalFramesDouble > static_cast<double>(audio.samples.max_size())) {
        bb.audio = std::move(audio);
        return;
    }

    const std::size_t totalFrames = static_cast<std::size_t>(totalFramesDouble);
    if (totalFrames == 0U) {
        bb.audio = std::move(audio);
        return;
    }
    audio.samples.assign(totalFrames, 0.0F);

    for (const Note& note : score.notes) {
        const Track* track = findTrack(score, note.trackId);
        if (track == nullptr || note.pitchMidi < 0 || note.pitchMidi > 127 ||
            !std::isfinite(note.startBeat) || !std::isfinite(note.durBeats) ||
            !std::isfinite(note.velocity) || !std::isfinite(track->gain) ||
            note.durBeats <= 0.0 || note.velocity <= 0.0 || track->gain == 0.0) {
            continue;
        }

        const double startBeat = std::max(0.0, note.startBeat);
        const double endBeat = std::min(score.lengthBeats, note.startBeat + note.durBeats);
        if (!std::isfinite(endBeat) || endBeat <= startBeat) {
            continue;
        }

        const double startFramesDouble = startBeat * secondsPerBeat *
                                         static_cast<double>(sampleRate);
        const double endFramesDouble = endBeat * secondsPerBeat *
                                       static_cast<double>(sampleRate);
        if (!std::isfinite(startFramesDouble) || !std::isfinite(endFramesDouble)) {
            continue;
        }
        const std::size_t startFrame = std::min(
            totalFrames, static_cast<std::size_t>(std::max(0.0, startFramesDouble)));
        const std::size_t endFrame = std::min(
            totalFrames, static_cast<std::size_t>(std::max(0.0, endFramesDouble)));
        if (endFrame <= startFrame) {
            continue;
        }

        const std::size_t noteFrames = endFrame - startFrame;
        const double amplitude = note.velocity * track->gain;
        if (track->role == Role::Drums) {
            const DrumVoice voice = drumVoiceForPitch(note.pitchMidi);
            const double decaySeconds = voice == DrumVoice::Kick ? 0.30
                                      : voice == DrumVoice::Snare ? 0.18
                                      : 0.08;
            const std::size_t drumFrames = std::min(
                noteFrames, static_cast<std::size_t>(decaySeconds * static_cast<double>(sampleRate)));
            for (std::size_t localFrame = 0; localFrame < drumFrames; ++localFrame) {
                const double sample = drumSampleAt(
                    voice, localFrame, startFrame, note.pitchMidi, sampleRate) * amplitude;
                if (std::isfinite(sample)) {
                    audio.samples[startFrame + localFrame] += static_cast<float>(sample);
                }
            }
        } else {
            const double frequencyHz = 440.0 * std::pow(
                2.0, static_cast<double>(note.pitchMidi - 69) / 12.0);
            if (!std::isfinite(frequencyHz) || frequencyHz <= 0.0) {
                continue;
            }

            const double phaseStep = kTwoPi * frequencyHz / static_cast<double>(sampleRate);
            const EnvelopeTimes envelope = envelopeForRole(track->role);
            for (std::size_t localFrame = 0; localFrame < noteFrames; ++localFrame) {
                const double phase = std::fmod(phaseStep * static_cast<double>(localFrame), kTwoPi);
                const double sample = oscillatorAt(track->osc, phase) *
                                      envelopeAt(localFrame, noteFrames, sampleRate, envelope) *
                                      amplitude;
                if (std::isfinite(sample)) {
                    audio.samples[startFrame + localFrame] += static_cast<float>(sample);
                }
            }
        }
    }

    double peak = 0.0;
    for (float& sample : audio.samples) {
        if (!std::isfinite(sample)) {
            sample = 0.0F;
            continue;
        }
        peak = std::max(peak, std::abs(static_cast<double>(sample)));
    }
    const double scale = peak > 0.0 ? 0.9 / peak : 1.0;
    for (float& sample : audio.samples) {
        const double scaled = static_cast<double>(sample) * scale;
        sample = static_cast<float>(std::isfinite(scaled)
                                        ? std::max(-1.0, std::min(1.0, scaled))
                                        : 0.0);
    }

    bb.audio = std::move(audio);
}

}  // namespace maestro