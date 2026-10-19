#include "maestro/Agent.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <random>
#include <string>
#include <vector>

namespace maestro {
namespace {

constexpr int kMelodyTrackId = 0;
constexpr int kChordsTrackId = 1;
constexpr double kBeatsPerChord = 4.0;

const std::array<int, 4>& progressionForMood(const std::string& mood) {
    static const std::array<int, 4> lofi = {0, 5, 2, 6};
    static const std::array<int, 4> chiptune = {0, 4, 5, 3};
    static const std::array<int, 4> cinematic = {0, 3, 5, 4};
    static const std::array<int, 4> ambient = {0, 5, 3, 4};

    if (mood == "chiptune") {
        return chiptune;
    }
    if (mood == "cinematic") {
        return cinematic;
    }
    if (mood == "ambient") {
        return ambient;
    }
    return lofi;
}

int scalePitch(const MusicalContext& context, int scaleDegree, int octave) {
    const int scaleSize = static_cast<int>(context.scaleSemitones.size());
    const int octaveShift = scaleDegree / scaleSize;
    const int degree = scaleDegree % scaleSize;
    return context.keyRootMidi + context.scaleSemitones[degree] +
           12 * (octave + octaveShift);
}

Osc melodyOscillator(const std::string& mood) {
    if (mood == "chiptune") {
        return Osc::Square;
    }
    if (mood == "cinematic") {
        return Osc::Saw;
    }
    if (mood == "ambient") {
        return Osc::Sine;
    }
    return Osc::Triangle;
}

Osc chordOscillator(const std::string& mood) {
    if (mood == "chiptune") {
        return Osc::Square;
    }
    if (mood == "cinematic") {
        return Osc::Saw;
    }
    return Osc::Triangle;
}

}  // namespace

void compose(Blackboard& bb) {
    MusicalContext context = bb.score.ctx;
    Score score;
    score.ctx = context;

    const double calculatedLength = bb.brief.seconds *
                                    static_cast<double>(score.ctx.tempoBpm) / 60.0;
    score.lengthBeats = std::isfinite(calculatedLength) && calculatedLength > 0.0
                            ? calculatedLength
                            : 0.0;
    score.tracks.push_back({kChordsTrackId, Role::Chords,
                            chordOscillator(bb.brief.mood), 0.62});
    score.tracks.push_back({kMelodyTrackId, Role::Melody,
                            melodyOscillator(bb.brief.mood), 0.74});

    if (score.lengthBeats <= 0.0 || score.ctx.scaleSemitones.empty()) {
        bb.score = std::move(score);
        return;
    }

    const std::array<int, 4>& progression = progressionForMood(bb.brief.mood);
    const int scaleSize = static_cast<int>(score.ctx.scaleSemitones.size());
    std::vector<int> chordRoots;
    for (double startBeat = 0.0; startBeat < score.lengthBeats;
         startBeat += kBeatsPerChord) {
        const int chordIndex = static_cast<int>(startBeat / kBeatsPerChord) %
                               static_cast<int>(progression.size());
        const int rootDegree = progression[static_cast<std::size_t>(chordIndex)] % scaleSize;
        chordRoots.push_back(rootDegree);
        const double duration = std::min(kBeatsPerChord, score.lengthBeats - startBeat);

        for (const int chordDegree : {rootDegree, rootDegree + 2, rootDegree + 4}) {
            score.notes.push_back({scalePitch(score.ctx, chordDegree, 0), startBeat,
                                   duration, 0.58, kChordsTrackId});
        }
    }

    const std::array<double, 4> durations = {0.5, 1.0, 1.5, 2.0};
    std::uniform_int_distribution<std::size_t> durationPick(0, durations.size() - 1U);
    std::uniform_int_distribution<int> chance(0, 99);
    std::uniform_int_distribution<int> passingTone(0, scaleSize - 1);

    for (double startBeat = 0.0; startBeat < score.lengthBeats;) {
        const double duration = std::min(durations[durationPick(score.ctx.rng)],
                                         score.lengthBeats - startBeat);
        if (chance(score.ctx.rng) < 18) {
            startBeat += duration;
            continue;
        }

        const int chordIndex = std::min(
            static_cast<int>(startBeat / kBeatsPerChord),
            static_cast<int>(chordRoots.size()) - 1);
        const int rootDegree = chordRoots[static_cast<std::size_t>(chordIndex)];
        const double beatInBar = std::fmod(startBeat, kBeatsPerChord);
        const bool strongBeat = beatInBar < 0.001 || std::abs(beatInBar - 2.0) < 0.001;
        const bool chooseChordTone = strongBeat || chance(score.ctx.rng) < 55;
        const int degree = chooseChordTone
                               ? rootDegree + 2 * (chance(score.ctx.rng) % 3)
                               : passingTone(score.ctx.rng);
        const int octave = chance(score.ctx.rng) < 70 ? 1 : 2;
        score.notes.push_back({scalePitch(score.ctx, degree, octave), startBeat,
                               duration, strongBeat ? 0.82 : 0.68, kMelodyTrackId});
        startBeat += duration;
    }

    bb.score = std::move(score);
}

}  // namespace maestro