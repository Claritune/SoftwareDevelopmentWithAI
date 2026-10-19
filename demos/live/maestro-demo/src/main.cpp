#include "maestro/Agent.h"

#include <cstdlib>
#include <exception>
#include <iostream>
#include <string>

namespace maestro {

Blackboard produce(const Brief& requestedBrief);
bool writeWav(const AudioBuffer& audio, const std::string& outputPath);

}  // namespace maestro

namespace {

std::string shellQuote(const std::string& value) {
    std::string quoted = "'";
    for (const char character : value) {
        if (character == '\'') {
            quoted += "'\\''";
        } else {
            quoted += character;
        }
    }
    return quoted + "'";
}

}  // namespace

int main(int argc, char* argv[]) {
    maestro::Brief brief;
    brief.seconds = 3.0;
    std::string outputPath = "song.wav";
    bool playAfterWrite = false;

    for (int argumentIndex = 1; argumentIndex < argc; ++argumentIndex) {
        const std::string argument = argv[argumentIndex];
        if ((argument == "--mood" || argument == "--key" || argument == "--scale" ||
             argument == "--tempo" || argument == "--seconds" || argument == "--seed" ||
             argument == "--passes" || argument == "--out") && argumentIndex + 1 >= argc) {
            std::cerr << "Missing value for " << argument << '\n';
            return 1;
        }
        try {
            if (argument == "--mood") {
                brief.mood = argv[++argumentIndex];
            } else if (argument == "--key") {
                brief.key = argv[++argumentIndex];
            } else if (argument == "--scale") {
                brief.scale = argv[++argumentIndex];
            } else if (argument == "--tempo") {
                brief.tempoBpm = std::stoi(argv[++argumentIndex]);
            } else if (argument == "--seconds") {
                brief.seconds = std::stod(argv[++argumentIndex]);
            } else if (argument == "--seed") {
                brief.seed = static_cast<std::uint32_t>(std::stoul(argv[++argumentIndex]));
            } else if (argument == "--passes") {
                brief.maxPasses = std::stoi(argv[++argumentIndex]);
            } else if (argument == "--out") {
                outputPath = argv[++argumentIndex];
            } else if (argument == "--play") {
                playAfterWrite = true;
            } else {
                std::cerr << "Unknown argument: " << argument << '\n';
                return 1;
            }
        } catch (const std::exception&) {
            std::cerr << "Invalid value for " << argument << '\n';
            return 1;
        }
    }

    const maestro::Blackboard result = maestro::produce(brief);
    if (!maestro::writeWav(result.audio, outputPath)) {
        std::cerr << "Unable to write WAV output: " << outputPath << '\n';
        return 1;
    }

    std::cout << "Wrote " << result.audio.samples.size() << " samples to " << outputPath
              << " after pass " << result.pass << '\n';
#if defined(__APPLE__)
    if (playAfterWrite && std::system(("afplay " + shellQuote(outputPath)).c_str()) != 0) {
        std::cerr << "Unable to play WAV output: " << outputPath << '\n';
        return 1;
    }
#else
    if (playAfterWrite) {
        std::cerr << "Playback is supported with afplay on macOS only\n";
        return 1;
    }
#endif
    return 0;
}