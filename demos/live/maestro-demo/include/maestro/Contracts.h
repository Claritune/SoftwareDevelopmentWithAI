#ifndef MAESTRO_CONTRACTS_H
#define MAESTRO_CONTRACTS_H

#include <cstdint>
#include <random>
#include <string>
#include <vector>

namespace maestro {

struct Brief {
    std::string mood = "lofi";
    std::string key = "A";
    std::string scale = "minor";
    int tempoBpm = 82;
    double seconds = 20.0;
    std::uint32_t seed = 7;
    int maxPasses = 2;
};

struct MusicalContext {
    int keyRootMidi = 69;
    std::vector<int> scaleSemitones;
    int tempoBpm = 82;
    int beatsPerBar = 4;
    int sampleRate = 44100;
    std::mt19937 rng;
};

enum class Osc { Sine, Square, Saw, Triangle, Noise };
enum class Role { Melody, Chords, Bass, Pad, Drums };

struct Note {
    int pitchMidi;
    double startBeat;
    double durBeats;
    double velocity;
    int trackId;
};

struct Track {
    int id;
    Role role;
    Osc osc;
    double gain = 0.8;
};

struct Score {
    MusicalContext ctx;
    std::vector<Track> tracks;
    std::vector<Note> notes;
    double lengthBeats = 0.0;
};

struct AudioBuffer {
    int sampleRate = 44100;
    int channels = 1;
    std::vector<float> samples;
};

struct Critique {
    double dissonance;
    double density;
    double dynamicRange;
    bool acceptable;
    std::vector<std::string> notes;
    std::string suggestedFix;
};

}  // namespace maestro

#endif  // MAESTRO_CONTRACTS_H