#include "maestro/Agent.h"

#include <algorithm>
#include <array>
#include <cctype>
#include <string>
#include <utility>
#include <vector>

namespace maestro {

void arrange(Blackboard& bb);
void compose(Blackboard& bb);
void critique(Blackboard& bb);
void synthesize(Blackboard& bb);

namespace {

struct KeyDefinition {
    const char* name;
    int pitchClass;
};

int keyRootMidi(const std::string& key) {
    static constexpr std::array<KeyDefinition, 17> keys = {{
        {"C", 0}, {"C#", 1}, {"Db", 1}, {"D", 2}, {"D#", 3}, {"Eb", 3},
        {"E", 4}, {"F", 5}, {"F#", 6}, {"Gb", 6}, {"G", 7}, {"G#", 8},
        {"Ab", 8}, {"A", 9}, {"A#", 10}, {"Bb", 10}, {"B", 11},
    }};
    for (const KeyDefinition& definition : keys) {
        if (key == definition.name) {
            return 60 + definition.pitchClass;
        }
    }
    return 69;
}

std::vector<int> scaleForName(const std::string& scale) {
    if (scale == "major") {
        return {0, 2, 4, 5, 7, 9, 11};
    }
    if (scale == "dorian") {
        return {0, 2, 3, 5, 7, 9, 10};
    }
    if (scale == "pentatonic") {
        return {0, 3, 5, 7, 10};
    }
    return {0, 2, 3, 5, 7, 8, 10};
}

void applySuggestedFix(Brief& brief, const std::string& suggestedFix) {
    if (suggestedFix == "raise_energy") {
        brief.tempoBpm = std::min(240, brief.tempoBpm + 8);
    } else if (suggestedFix == "reduce_density") {
        brief.tempoBpm = std::max(40, brief.tempoBpm - 8);
    }
}

}  // namespace

Blackboard produce(const Brief& requestedBrief) {
    Blackboard bb;
    bb.brief = requestedBrief;

    for (int pass = 0;; ++pass) {
        bb.pass = pass;
        bb.score = Score{};
        bb.audio = AudioBuffer{};
        bb.critique = Critique{};
        bb.score.ctx.keyRootMidi = keyRootMidi(bb.brief.key);
        bb.score.ctx.scaleSemitones = scaleForName(bb.brief.scale);
        bb.score.ctx.tempoBpm = bb.brief.tempoBpm;
        bb.score.ctx.beatsPerBar = 4;
        bb.score.ctx.sampleRate = 44100;
        bb.score.ctx.rng.seed(bb.brief.seed);

        compose(bb);
        arrange(bb);
        synthesize(bb);
        critique(bb);

        if (bb.critique.acceptable || pass >= std::max(0, bb.brief.maxPasses) ||
            bb.critique.suggestedFix.empty()) {
            return bb;
        }
        applySuggestedFix(bb.brief, bb.critique.suggestedFix);
    }
}

}  // namespace maestro