#include "maestro/Agent.h"
#include "../src/Producer.cpp"

#include <cmath>
#include <iostream>
#include <string>
#include <vector>

namespace maestro {
void compose(Blackboard& bb);
void critique(Blackboard& bb);
void synthesize(Blackboard& bb);
}

namespace {

constexpr double kEpsilon = 1e-9;

maestro::Blackboard makeSeededBlackboard() {
    maestro::Blackboard bb;
    bb.brief.mood = "lofi";
    bb.brief.key = "A";
    bb.brief.scale = "minor";
    bb.brief.tempoBpm = 120;
    bb.brief.seconds = 12.0;
    bb.brief.seed = 20260907;

    bb.score.ctx.keyRootMidi = 69;
    bb.score.ctx.scaleSemitones = {0, 2, 3, 5, 7, 8, 10};
    bb.score.ctx.tempoBpm = bb.brief.tempoBpm;
    bb.score.ctx.beatsPerBar = 4;
    bb.score.ctx.sampleRate = 44100;
    bb.score.ctx.rng.seed(bb.brief.seed);
    return bb;
}

maestro::Blackboard makeCriticBlackboard() {
    maestro::Blackboard bb = makeSeededBlackboard();
    bb.score.lengthBeats = 4.0;
    bb.score.tracks = {{1, maestro::Role::Melody, maestro::Osc::Sine}};
    bb.score.notes.clear();
    bb.audio.samples.clear();
    return bb;
}

void addNote(maestro::Blackboard& bb, int pitchMidi, double startBeat, double velocity) {
    bb.score.notes.push_back({pitchMidi, startBeat, 0.25, velocity, 1});
}

int pitchClass(int pitchMidi) {
    const int pitchClass = pitchMidi % 12;
    return pitchClass < 0 ? pitchClass + 12 : pitchClass;
}

bool isInConfiguredScale(const maestro::Score& score, int pitchMidi) {
    const int interval = (pitchClass(pitchMidi) - pitchClass(score.ctx.keyRootMidi) + 12) % 12;
    for (const int scaleSemitone : score.ctx.scaleSemitones) {
        if (interval == scaleSemitone) {
            return true;
        }
    }
    return false;
}

bool hasTrack(const maestro::Score& score, maestro::Role role, int* trackId) {
    for (const maestro::Track& track : score.tracks) {
        if (track.role == role) {
            *trackId = track.id;
            return true;
        }
    }
    return false;
}

bool hasNoteOnTrack(const maestro::Score& score, int trackId) {
    for (const maestro::Note& note : score.notes) {
        if (note.trackId == trackId) {
            return true;
        }
    }
    return false;
}

bool equivalentSymbolicScore(const maestro::Score& left, const maestro::Score& right) {
    if (left.ctx.keyRootMidi != right.ctx.keyRootMidi ||
        left.ctx.scaleSemitones != right.ctx.scaleSemitones ||
        left.ctx.tempoBpm != right.ctx.tempoBpm ||
        left.ctx.beatsPerBar != right.ctx.beatsPerBar ||
        left.ctx.sampleRate != right.ctx.sampleRate ||
        left.lengthBeats != right.lengthBeats ||
        left.tracks.size() != right.tracks.size() ||
        left.notes.size() != right.notes.size()) {
        return false;
    }

    for (std::size_t index = 0; index < left.tracks.size(); ++index) {
        const maestro::Track& lhs = left.tracks[index];
        const maestro::Track& rhs = right.tracks[index];
        if (lhs.id != rhs.id || lhs.role != rhs.role || lhs.osc != rhs.osc || lhs.gain != rhs.gain) {
            return false;
        }
    }

    for (std::size_t index = 0; index < left.notes.size(); ++index) {
        const maestro::Note& lhs = left.notes[index];
        const maestro::Note& rhs = right.notes[index];
        if (lhs.pitchMidi != rhs.pitchMidi || lhs.startBeat != rhs.startBeat ||
            lhs.durBeats != rhs.durBeats || lhs.velocity != rhs.velocity ||
            lhs.trackId != rhs.trackId) {
            return false;
        }
    }
    return true;
}

int fail(const std::string& message);

bool isAllowedSuggestedFix(const std::string& suggestedFix) {
    return suggestedFix == "resolve_dissonance" || suggestedFix == "reduce_density" ||
           suggestedFix == "raise_energy";
}

int verifyAudioSamples(const maestro::AudioBuffer& audio, const std::string& context) {
    if (audio.samples.empty()) {
        return fail(context + ": expected nonempty samples, got 0 samples");
    }
    for (std::size_t index = 0; index < audio.samples.size(); ++index) {
        const float sample = audio.samples[index];
        if (!std::isfinite(sample)) {
            return fail(context + ": sample " + std::to_string(index) +
                        " is not finite (got " + std::to_string(sample) + ")");
        }
        if (sample < -1.0F || sample > 1.0F) {
            return fail(context + ": sample " + std::to_string(index) +
                        " is outside [-1, 1] (got " + std::to_string(sample) + ")");
        }
    }
    return 0;
}

int fail(const std::string& message) {
    std::cerr << "FAIL: " << message << '\n';
    return 1;
}

}  // namespace

int main() {
    maestro::Brief deterministicBrief;
    deterministicBrief.mood = "lofi";
    deterministicBrief.key = "A";
    deterministicBrief.scale = "minor";
    deterministicBrief.tempoBpm = 82;
    deterministicBrief.seconds = 20.0;
    deterministicBrief.seed = 7;
    deterministicBrief.maxPasses = 2;
    const maestro::Blackboard firstProduction = maestro::produce(deterministicBrief);
    const maestro::Blackboard secondProduction = maestro::produce(deterministicBrief);

    if (!equivalentSymbolicScore(firstProduction.score, secondProduction.score)) {
        return fail("production determinism: equal briefs produced different symbolic scores");
    }
    if (firstProduction.audio.samples != secondProduction.audio.samples) {
        return fail("production determinism: equal briefs produced different audio samples");
    }
    if (verifyAudioSamples(firstProduction.audio, "production audio") != 0) {
        return 1;
    }

    maestro::Brief retryBrief = deterministicBrief;
    retryBrief.mood = "ambient";
    const maestro::Blackboard retryProduction = maestro::produce(retryBrief);
    if (retryProduction.pass <= 0 || retryProduction.pass > retryBrief.maxPasses) {
        return fail("production retry: ambient seed 7 expected pass in [1, " +
                    std::to_string(retryBrief.maxPasses) + "], got " +
                    std::to_string(retryProduction.pass));
    }
    if (retryProduction.critique.acceptable) {
        if (!retryProduction.critique.suggestedFix.empty()) {
            return fail("production retry: acceptable final result expected no suggested fix, got " +
                        retryProduction.critique.suggestedFix);
        }
    } else if (!isAllowedSuggestedFix(retryProduction.critique.suggestedFix)) {
        return fail("production retry: unacceptable final result expected an allowed suggested "
                    "fix, got " + retryProduction.critique.suggestedFix);
    }

    maestro::Blackboard dissonant = makeCriticBlackboard();
    addNote(dissonant, 60, 0.0, 0.25);
    addNote(dissonant, 61, 0.0, 0.80);
    for (int index = 0; index < 6; ++index) {
        addNote(dissonant, 60, 0.5 + static_cast<double>(index) * 0.5,
                index % 2 == 0 ? 0.25 : 0.80);
    }
    maestro::critique(dissonant);
    if (dissonant.critique.acceptable ||
        dissonant.critique.suggestedFix != "resolve_dissonance") {
        return fail("critic dissonance: concurrent minor second expected unacceptable with "
                    "resolve_dissonance, got acceptable=" +
                    std::string(dissonant.critique.acceptable ? "true" : "false") +
                    ", suggestedFix=" + dissonant.critique.suggestedFix);
    }

    maestro::Blackboard dense = makeCriticBlackboard();
    for (int index = 0; index < 21; ++index) {
        addNote(dense, 60, static_cast<double>(index) * 0.18,
                index % 2 == 0 ? 0.25 : 0.80);
    }
    maestro::critique(dense);
    if (dense.critique.acceptable || dense.critique.suggestedFix != "reduce_density") {
        return fail("critic density: 21 valid lofi notes in one bar expected unacceptable with "
                    "reduce_density, got acceptable=" +
                    std::string(dense.critique.acceptable ? "true" : "false") +
                    ", suggestedFix=" + dense.critique.suggestedFix);
    }

    maestro::Blackboard flatDynamics = makeCriticBlackboard();
    for (int index = 0; index < 8; ++index) {
        addNote(flatDynamics, 60, static_cast<double>(index) * 0.5, 0.50);
    }
    maestro::critique(flatDynamics);
    if (flatDynamics.critique.acceptable ||
        flatDynamics.critique.suggestedFix != "raise_energy") {
        return fail("critic dynamics: flat 0.50 velocities with no audio expected unacceptable "
                    "with raise_energy, got acceptable=" +
                    std::string(flatDynamics.critique.acceptable ? "true" : "false") +
                    ", suggestedFix=" + flatDynamics.critique.suggestedFix);
    }

    maestro::Blackboard balanced = makeCriticBlackboard();
    for (int index = 0; index < 8; ++index) {
        addNote(balanced, 60, static_cast<double>(index) * 0.5,
                index % 2 == 0 ? 0.25 : 0.80);
    }
    maestro::critique(balanced);
    if (!balanced.critique.acceptable || !balanced.critique.suggestedFix.empty()) {
        return fail("critic balanced: 8 non-overlapping lofi notes with varied velocities "
                    "expected acceptable with no suggested fix, got acceptable=" +
                    std::string(balanced.critique.acceptable ? "true" : "false") +
                    ", suggestedFix=" + balanced.critique.suggestedFix);
    }

    maestro::Blackboard first = makeSeededBlackboard();
    maestro::Blackboard second = first;
    maestro::Blackboard differentMood = first;
    differentMood.brief.mood = "chiptune";

    maestro::compose(first);
    maestro::compose(second);
    maestro::compose(differentMood);
    maestro::synthesize(first);

    if (first.audio.channels != 1) {
        return fail("audio: expected mono output with 1 channel, got " +
                    std::to_string(first.audio.channels));
    }
    if (first.audio.sampleRate != first.score.ctx.sampleRate) {
        return fail("audio: expected sample rate " +
                    std::to_string(first.score.ctx.sampleRate) + ", got " +
                    std::to_string(first.audio.sampleRate));
    }
    if (verifyAudioSamples(first.audio, "audio") != 0) {
        return 1;
    }

    if (!equivalentSymbolicScore(first.score, second.score)) {
        return fail("determinism: equal seeded blackboards produced different symbolic scores");
    }
    if (equivalentSymbolicScore(first.score, differentMood.score)) {
        return fail("mood: lofi and chiptune produced identical symbolic scores");
    }

    const double expectedLengthBeats = first.brief.seconds * first.brief.tempoBpm / 60.0;
    if (first.score.lengthBeats <= 0.0 ||
        std::abs(first.score.lengthBeats - expectedLengthBeats) > kEpsilon) {
        return fail("length: expected " + std::to_string(expectedLengthBeats) +
                    " beats from 12.000000 seconds at 120 BPM, got " +
                    std::to_string(first.score.lengthBeats));
    }

    int melodyTrackId = 0;
    if (!hasTrack(first.score, maestro::Role::Melody, &melodyTrackId)) {
        return fail("arrangement: expected a Melody track, found none");
    }
    if (!hasNoteOnTrack(first.score, melodyTrackId)) {
        return fail("arrangement: expected at least one note on the Melody track id " +
                    std::to_string(melodyTrackId));
    }

    int chordsTrackId = 0;
    if (!hasTrack(first.score, maestro::Role::Chords, &chordsTrackId)) {
        return fail("arrangement: expected a Chords track, found none");
    }
    if (!hasNoteOnTrack(first.score, chordsTrackId)) {
        return fail("arrangement: expected at least one note on the Chords track id " +
                    std::to_string(chordsTrackId));
    }

    for (const maestro::Note& note : first.score.notes) {
        bool isDrumNote = false;
        for (const maestro::Track& track : first.score.tracks) {
            if (track.id == note.trackId && track.role == maestro::Role::Drums) {
                isDrumNote = true;
                break;
            }
        }
        if (!isDrumNote && !isInConfiguredScale(first.score, note.pitchMidi)) {
            return fail("scale: non-drum pitch " + std::to_string(note.pitchMidi) +
                        " is outside the configured A minor scale");
        }
    }

    return 0;
}