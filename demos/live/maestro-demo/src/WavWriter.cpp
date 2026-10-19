#include "maestro/Contracts.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <limits>
#include <string>

namespace maestro {
namespace {

void writeLittleEndian16(std::ofstream& stream, std::uint16_t value) {
    stream.put(static_cast<char>(value & 0xffU));
    stream.put(static_cast<char>((value >> 8U) & 0xffU));
}

void writeLittleEndian32(std::ofstream& stream, std::uint32_t value) {
    stream.put(static_cast<char>(value & 0xffU));
    stream.put(static_cast<char>((value >> 8U) & 0xffU));
    stream.put(static_cast<char>((value >> 16U) & 0xffU));
    stream.put(static_cast<char>((value >> 24U) & 0xffU));
}

}  // namespace

bool writeWav(const AudioBuffer& audio, const std::string& outputPath) {
    if (audio.sampleRate <= 0 || audio.channels <= 0 || audio.samples.empty() ||
        audio.samples.size() % static_cast<std::size_t>(audio.channels) != 0U) {
        return false;
    }

    constexpr std::uint16_t bitsPerSample = 16;
    constexpr std::uint16_t bytesPerSample = bitsPerSample / 8U;
    const auto channelCount = static_cast<std::uint64_t>(audio.channels);
    const auto sampleRate = static_cast<std::uint64_t>(audio.sampleRate);
    const std::uint64_t blockAlign = channelCount * bytesPerSample;
    const std::uint64_t byteRate = sampleRate * blockAlign;
    const std::uint64_t dataSize = static_cast<std::uint64_t>(audio.samples.size()) * bytesPerSample;

    if (channelCount > std::numeric_limits<std::uint16_t>::max() ||
        blockAlign > std::numeric_limits<std::uint16_t>::max() ||
        byteRate > std::numeric_limits<std::uint32_t>::max() ||
        dataSize > std::numeric_limits<std::uint32_t>::max() ||
        dataSize + 36U > std::numeric_limits<std::uint32_t>::max()) {
        return false;
    }

    std::ofstream stream(outputPath, std::ios::binary);
    if (!stream) {
        return false;
    }

    stream.write("RIFF", 4);
    writeLittleEndian32(stream, static_cast<std::uint32_t>(dataSize + 36U));
    stream.write("WAVEfmt ", 8);
    writeLittleEndian32(stream, 16U);
    writeLittleEndian16(stream, 1U);
    writeLittleEndian16(stream, static_cast<std::uint16_t>(channelCount));
    writeLittleEndian32(stream, static_cast<std::uint32_t>(sampleRate));
    writeLittleEndian32(stream, static_cast<std::uint32_t>(byteRate));
    writeLittleEndian16(stream, static_cast<std::uint16_t>(blockAlign));
    writeLittleEndian16(stream, bitsPerSample);
    stream.write("data", 4);
    writeLittleEndian32(stream, static_cast<std::uint32_t>(dataSize));

    for (float sample : audio.samples) {
        const float boundedSample = std::isfinite(sample)
                                        ? std::clamp(sample, -1.0F, 1.0F)
                                        : 0.0F;
        const auto pcmSample = static_cast<std::int16_t>(
            std::lround(boundedSample * static_cast<float>(std::numeric_limits<std::int16_t>::max())));
        writeLittleEndian16(stream, static_cast<std::uint16_t>(pcmSample));
    }

    return static_cast<bool>(stream);
}

}  // namespace maestro