#include "maestro/Agent.h"

#include <algorithm>
#include <cmath>
#include <string>
#include <vector>

namespace maestro {
namespace {

constexpr int kBassTrackId = 2;
constexpr int kPadTrackId = 3;
constexpr int kDrumsTrackId = 4;
constexpr double kTimingEpsilon = 1e-9;

bool hasTrack(const Score& score, Role role) {
    return std::any_of(score.tracks.begin(), score.tracks.end(),
                       [role](const Track& track) { return track.role == role; });
}

bool hasTrackId(const Score& score, int trackId) {
    return std::any_of(score.tracks.begin(), score.tracks.end(),
                       [trackId](const Track& track) { return track.id == trackId; });
}

Osc bassOscillator(const std::string& mood) {
    if (mood == "chiptune") {
        return Osc::Square;
    }
    if (mood == "cinematic") {
        return Osc::Saw;
    }
    return Osc::Sine;
}

Osc padOscillator(const std::string& mood) {
    if (mood == "chiptune") {
        return Osc::Triangle;
    }
    if (mood == "cinematic") {
        return Osc::Saw;
    }
    return Osc::Sine;
}

double bassGain(const std::string& mood) {
    if (mood == "chiptune") {
        return 0.58;
    }
    if (mood == "cinematic") {
        return 0.70;
    }
    if (mood == "ambient") {
        return 0.48;
    }
    return 0.64;
}

double padGain(const std::string& mood) {
    if (mood == "chiptune") {
        return 0.28;
    }
    if (mood == "cinematic") {
        return 0.46;
    }
    if (mood == "ambient") {
        return 0.52;
    }
    return 0.38;
}

double drumGain(const std::string& mood) {
    if (mood == "chiptune") {
        return 0.44;
    }
    if (mood == "cinematic") {
        return 0.58;
    }
    if (mood == "ambient") {
        return 0.34;
    }
    return 0.52;
}

struct ChordEvent {
    double startBeat;
    double duration;
    std::vector<int> pitches;
};

std::vector<ChordEvent> chordEvents(const Score& score) {
    std::vector<ChordEvent> events;
    for (const Note& note : score.notes) {
        if (note.trackId != 1) {
            continue;
        }

        auto event = std::find_if(events.begin(), events.end(), [&note](const ChordEvent& value) {
            return std::abs(value.startBeat - note.startBeat) < kTimingEpsilon;
        });
        if (event == events.end()) {
            events.push_back({note.startBeat, note.durBeats, {note.pitchMidi}});
        } else {
            event->duration = std::max(event->duration, note.durBeats);
            event->pitches.push_back(note.pitchMidi);
        }
    }
    return events;
}

void addDrums(Score& score) {
    const int beatsPerBar = std::max(1, score.ctx.beatsPerBar);
    const double hatSpacing = score.ctx.tempoBpm >= 110 ? 0.5 : 1.0;
    for (double barStart = 0.0; barStart < score.lengthBeats; barStart += beatsPerBar) {
        const double barEnd = std::min(barStart + beatsPerBar, score.lengthBeats);
        for (double startBeat = barStart; startBeat < barEnd; startBeat += hatSpacing) {
            score.notes.push_back({42, startBeat, std::min(0.12, barEnd - startBeat),
                                   0.34, kDrumsTrackId});
        }
        for (double startBeat = barStart; startBeat < barEnd; startBeat += 2.0) {
            score.notes.push_back({36, startBeat, std::min(0.22, barEnd - startBeat),
                                   0.82, kDrumsTrackId});
        }
        for (double startBeat = barStart + 1.0; startBeat < barEnd; startBeat += 2.0) {
            score.notes.push_back({38, startBeat, std::min(0.18, barEnd - startBeat),
                                   0.68, kDrumsTrackId});
        }
    }
}

}  // namespace

void arrange(Blackboard& bb) {
    Score& score = bb.score;
    if (hasTrack(score, Role::Bass) || hasTrack(score, Role::Pad) ||
        hasTrack(score, Role::Drums) || hasTrackId(score, kBassTrackId) ||
        hasTrackId(score, kPadTrackId) || hasTrackId(score, kDrumsTrackId)) {
        return;
    }

    score.tracks.push_back(
        {kBassTrackId, Role::Bass, bassOscillator(bb.brief.mood), bassGain(bb.brief.mood)});
    score.tracks.push_back(
        {kPadTrackId, Role::Pad, padOscillator(bb.brief.mood), padGain(bb.brief.mood)});
    score.tracks.push_back({kDrumsTrackId, Role::Drums, Osc::Noise, drumGain(bb.brief.mood)});

    const std::vector<ChordEvent> events = chordEvents(score);
    for (const ChordEvent& event : events) {
        if (event.pitches.empty() || event.duration <= 0.0) {
            continue;
        }
        const int root = *std::min_element(event.pitches.begin(), event.pitches.end());
        score.notes.push_back({root - 12, event.startBeat, event.duration, 0.72, kBassTrackId});
        for (const int pitch : event.pitches) {
            score.notes.push_back({pitch, event.startBeat, event.duration, 0.42, kPadTrackId});
        }
    }

    if (score.lengthBeats > 0.0) {
        addDrums(score);
    }
}

}  // namespace maestro