#ifndef MAESTRO_AGENT_H
#define MAESTRO_AGENT_H

#include "maestro/Contracts.h"

namespace maestro {

struct Blackboard {
    Brief brief;
    Score score;
    AudioBuffer audio;
    Critique critique;
    int pass = 0;
};

class Agent {
public:
    virtual ~Agent() = default;
    virtual const char* name() const = 0;
    virtual void process(Blackboard& bb) = 0;
};

}  // namespace maestro

#endif  // MAESTRO_AGENT_H