#include "maestro/Agent.h"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <sstream>
#include <string>
#include <vector>

namespace maestro {
namespace {

struct DensityBand {
    double minimum;
    double target;
    double maximum;
};

DensityBand densityBandForMood(const std::string& mood) {
    if (mood == "ambient") {
        return {3.0, 6.0, 10.0};
    }
    if (mood == "cinematic") {
        return {5.0, 10.0, 16.0};
    }
    if (mood == "chiptune") {
        return {12.0, 20.0, 30.0};
    }
    return {8.0, 13.0, 20.0};
}

bool isDrumNote(const Score& score, int trackId) {
    for (const Track& track : score.tracks) {
        if (track.id == trackId) {
            return track.role == Role::Drums;
        }
    }
    return false;
}

bool isValidNote(const Note& note) {
    return note.pitchMidi >= 0 && note.pitchMidi <= 127 &&
           std::isfinite(note.startBeat) && std::isfinite(note.durBeats) &&
           std::isfinite(note.velocity) && note.durBeats > 0.0;
}

int pitchClassDistance(int left, int right) {
    const int distance = std::abs(left - right) % 12;
    return std::min(distance, 12 - distance);
}

std::string metricNote(const char* label, double value) {
    std::ostringstream stream;
    stream.setf(std::ios::fixed);
    stream.precision(2);
    stream << label << value;
    return stream.str();
}

}  // namespace

void critique(Blackboard& bb) {
    Critique result{};
    result.dissonance = 0.0;
    result.density = 0.0;
    result.dynamicRange = 0.0;
    result.acceptable = false;

    bool invalidInput = !std::isfinite(bb.score.lengthBeats) ||
                        !std::isfinite(bb.brief.seconds);
    std::vector<const Note*> validNotes;
    validNotes.reserve(bb.score.notes.size());
    double minimumVelocity = 1.0;
    double maximumVelocity = 0.0;

    for (const Note& note : bb.score.notes) {
        if (!isValidNote(note)) {
            invalidInput = true;
            continue;
        }
        validNotes.push_back(&note);
        const double velocity = std::clamp(note.velocity, 0.0, 1.0);
        minimumVelocity = std::min(minimumVelocity, velocity);
        maximumVelocity = std::max(maximumVelocity, velocity);
    }

    const int beatsPerBar = bb.score.ctx.beatsPerBar;
    double lengthBeats = bb.score.lengthBeats;
    if (lengthBeats <= 0.0 && std::isfinite(bb.brief.seconds) &&
        bb.brief.seconds > 0.0 && bb.score.ctx.tempoBpm > 0) {
        lengthBeats = bb.brief.seconds * static_cast<double>(bb.score.ctx.tempoBpm) / 60.0;
    }
    if (beatsPerBar <= 0 || !std::isfinite(lengthBeats) || lengthBeats <= 0.0) {
        invalidInput = true;
    } else {
        const double bars = lengthBeats / static_cast<double>(beatsPerBar);
        const DensityBand band = densityBandForMood(bb.brief.mood);
        const double notesPerBar = static_cast<double>(validNotes.size()) / bars;
        result.density = std::clamp(notesPerBar / band.target, 0.0, 1.0);
        if (notesPerBar < band.minimum || notesPerBar > band.maximum) {
            result.notes.push_back(metricNote("Density is ", notesPerBar) +
                                   " notes per bar; target band is " +
                                   metricNote("", band.minimum) + " to " +
                                   metricNote("", band.maximum) + ".");
        }
    }

    std::size_t intervalCount = 0;
    std::size_t dissonantCount = 0;
    for (std::size_t leftIndex = 0; leftIndex < validNotes.size(); ++leftIndex) {
        const Note& left = *validNotes[leftIndex];
        if (isDrumNote(bb.score, left.trackId)) {
            continue;
        }
        const double leftEnd = left.startBeat + left.durBeats;
        for (std::size_t rightIndex = leftIndex + 1; rightIndex < validNotes.size(); ++rightIndex) {
            const Note& right = *validNotes[rightIndex];
            if (isDrumNote(bb.score, right.trackId)) {
                continue;
            }
            const double rightEnd = right.startBeat + right.durBeats;
            if (left.startBeat < rightEnd && right.startBeat < leftEnd) {
                ++intervalCount;
                const int interval = pitchClassDistance(left.pitchMidi, right.pitchMidi);
                if (interval == 1 || interval == 6) {
                    ++dissonantCount;
                }
            }
        }
    }
    if (intervalCount > 0) {
        result.dissonance = static_cast<double>(dissonantCount) /
                             static_cast<double>(intervalCount);
    }

    bool usableAudio = !bb.audio.samples.empty();
    double sumSquares = 0.0;
    double peak = 0.0;
    if (usableAudio) {
        for (const float sample : bb.audio.samples) {
            if (!std::isfinite(sample)) {
                invalidInput = true;
                usableAudio = false;
                break;
            }
            const double magnitude = std::abs(static_cast<double>(sample));
            peak = std::max(peak, magnitude);
            sumSquares += magnitude * magnitude;
        }
    }
    if (usableAudio && peak > 0.0 && std::isfinite(sumSquares)) {
        const double rms = std::sqrt(sumSquares / static_cast<double>(bb.audio.samples.size()));
        result.dynamicRange = std::clamp(1.0 - rms / peak, 0.0, 1.0);
    } else if (!validNotes.empty()) {
        result.dynamicRange = maximumVelocity - minimumVelocity;
    }

    const DensityBand band = densityBandForMood(bb.brief.mood);
    const bool hasUsableLength = beatsPerBar > 0 && std::isfinite(lengthBeats) && lengthBeats > 0.0;
    const double notesPerBar = hasUsableLength
                                   ? static_cast<double>(validNotes.size()) /
                                         (lengthBeats / static_cast<double>(beatsPerBar))
                                   : 0.0;
    const bool densityAcceptable = hasUsableLength && notesPerBar >= band.minimum &&
                                   notesPerBar <= band.maximum;
    const bool dissonanceAcceptable = result.dissonance <= 0.20;
    const bool dynamicsAcceptable = result.dynamicRange >= 0.12;

    if (invalidInput) {
        result.notes.push_back("Score or audio contains invalid timing, velocity, or sample data.");
    }
    if (result.dissonance > 0.20) {
        result.notes.push_back(metricNote("Dissonance fraction is ", result.dissonance) +
                               "; maximum is 0.20.");
    }
    if (result.dynamicRange < 0.12) {
        result.notes.push_back(metricNote("Dynamic range is ", result.dynamicRange) +
                               "; minimum is 0.12.");
    }

    result.acceptable = !invalidInput && densityAcceptable && dissonanceAcceptable &&
                        dynamicsAcceptable;
    if (!result.acceptable) {
        if (result.dissonance > 0.20) {
            result.suggestedFix = "resolve_dissonance";
        } else if (!densityAcceptable && notesPerBar > band.maximum) {
            result.suggestedFix = "reduce_density";
        } else {
            result.suggestedFix = "raise_energy";
        }
    }

    bb.critique = result;
}

}  // namespace maestro