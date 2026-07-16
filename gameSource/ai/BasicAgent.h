#ifndef BASIC_AGENT_INCLUDED
#define BASIC_AGENT_INCLUDED

#include <cstdio>
#include <vector>

struct VisibleObject {
    int objectID;
    int x;
    int y;
    int distance;
    int foodValue;
    bool pickupable;
    int emptyHandFoodResultID;
    int requiredToolID;
    int toolFoodResultID;
};

struct AgentObservation {
    int x;
    int y;
    int heldObjectID;
    int heldObjectFoodValue;
    int foodStore;
    int foodCapacity;
    int maxFoodStore;
    int maxFoodCapacity;
    double age;
    double currentTime;
    bool inMotion;
    std::vector<VisibleObject> nearbyObjects;
};

enum class AgentActionType {
    NONE,
    MOVE_TO,
    INTERACT,
    EAT,
    DROP
};

struct AgentAction {
    AgentActionType type;
    int targetX;
    int targetY;
};

class BasicAgent {
    public:
        BasicAgent()
            : mEnabled( true ),
              mNextDebugTime( 0.0 ),
              mLastActionTime( -100.0 ),
              mLastTargetX( 0 ),
              mLastTargetY( 0 ) {
        }

        AgentAction decide( const AgentObservation &inObservation ) {
            AgentAction none = makeAction( AgentActionType::NONE, 0, 0 );

            if( !mEnabled ) {
                return none;
            }

            printDebug( inObservation );

            if( inObservation.inMotion ||
                inObservation.currentTime - mLastActionTime < 0.35 ) {
                return none;
            }

            bool hungry =
                inObservation.foodStore <=
                ( inObservation.foodCapacity * 2 ) / 3;

            if( hungry ) {
                if( inObservation.heldObjectID > 0 &&
                    inObservation.heldObjectFoodValue > 0 ) {
                    return issue( AgentActionType::EAT,
                                  inObservation.x,
                                  inObservation.y,
                                  inObservation.currentTime,
                                  "held food" );
                }

                const VisibleObject *looseFood =
                    findNearestLooseFood( inObservation );

                if( looseFood != NULL ) {
                    if( inObservation.heldObjectID != 0 ) {
                        return dropHeldObject( inObservation );
                    }
                    return approachOrInteract(
                        *looseFood, inObservation.currentTime, "loose food" );
                }

                const VisibleObject *bareSource =
                    findNearestBareHandSource( inObservation );

                if( bareSource != NULL ) {
                    if( inObservation.heldObjectID != 0 ) {
                        return dropHeldObject( inObservation );
                    }
                    return approachOrInteract(
                        *bareSource,
                        inObservation.currentTime,
                        "empty-hand food source" );
                }

                ToolPlan plan = findNearestToolPlan( inObservation );

                if( plan.source != NULL &&
                    inObservation.heldObjectID ==
                    plan.source->requiredToolID ) {
                    return approachOrInteract(
                        *plan.source,
                        inObservation.currentTime,
                        "tool food source" );
                }

                if( plan.source != NULL && plan.tool != NULL ) {
                    if( inObservation.heldObjectID != 0 ) {
                        return dropHeldObject( inObservation );
                    }
                    return approachOrInteract(
                        *plan.tool,
                        inObservation.currentTime,
                        "required food tool" );
                }
            }

            const VisibleObject *wander = findWanderTarget( inObservation );

            if( wander != NULL ) {
                return issue( AgentActionType::MOVE_TO,
                              wander->x,
                              wander->y,
                              inObservation.currentTime,
                              hungry ? "forage" : "explore" );
            }

            return none;
        }

        void observe( const AgentObservation &inObservation ) {
            if( mEnabled ) {
                printDebug( inObservation );
            }
        }

        void setEnabled( bool inEnabled ) {
            mEnabled = inEnabled;
        }

        void reset() {
            mNextDebugTime = 0.0;
            mLastActionTime = -100.0;
            mLastTargetX = 0;
            mLastTargetY = 0;
        }

    private:
        struct ToolPlan {
            const VisibleObject *source;
            const VisibleObject *tool;
        };

        bool mEnabled;
        double mNextDebugTime;
        double mLastActionTime;
        int mLastTargetX;
        int mLastTargetY;

        AgentAction makeAction(
            AgentActionType inType, int inX, int inY ) const {
            AgentAction action;
            action.type = inType;
            action.targetX = inX;
            action.targetY = inY;
            return action;
        }

        AgentAction issue(
            AgentActionType inType,
            int inX,
            int inY,
            double inTime,
            const char *inReason ) {
            mLastActionTime = inTime;
            mLastTargetX = inX;
            mLastTargetY = inY;

            std::printf(
                "AGENT ACTION: %s x=%d y=%d reason=%s\n",
                actionName( inType ), inX, inY, inReason );

            return makeAction( inType, inX, inY );
        }

        AgentAction approachOrInteract(
            const VisibleObject &inTarget,
            double inTime,
            const char *inReason ) {
            if( inTarget.distance <= 1 ) {
                return issue( AgentActionType::INTERACT,
                              inTarget.x,
                              inTarget.y,
                              inTime,
                              inReason );
            }

            return issue( AgentActionType::MOVE_TO,
                          inTarget.x,
                          inTarget.y,
                          inTime,
                          inReason );
        }

        AgentAction dropHeldObject(
            const AgentObservation &inObservation ) {
            static const int offsets[4][2] = {
                { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }
            };

            for( int i=0; i<4; i++ ) {
                int x = inObservation.x + offsets[i][0];
                int y = inObservation.y + offsets[i][1];

                if( !hasObjectAt( inObservation, x, y ) ) {
                    return issue( AgentActionType::DROP,
                                  x,
                                  y,
                                  inObservation.currentTime,
                                  "clear hand" );
                }
            }

            return makeAction( AgentActionType::NONE, 0, 0 );
        }

        bool hasObjectAt(
            const AgentObservation &inObservation,
            int inX,
            int inY ) const {
            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];
                if( o.x == inX && o.y == inY ) {
                    return true;
                }
            }
            return false;
        }

        const VisibleObject *findNearestLooseFood(
            const AgentObservation &inObservation ) const {
            const VisibleObject *best = NULL;

            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];
                if( o.foodValue > 0 && o.pickupable &&
                    ( best == NULL || o.distance < best->distance ) ) {
                    best = &o;
                }
            }
            return best;
        }

        const VisibleObject *findNearestBareHandSource(
            const AgentObservation &inObservation ) const {
            const VisibleObject *best = NULL;

            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];
                if( o.emptyHandFoodResultID > 0 &&
                    ( best == NULL || o.distance < best->distance ) ) {
                    best = &o;
                }
            }
            return best;
        }

        ToolPlan findNearestToolPlan(
            const AgentObservation &inObservation ) const {
            ToolPlan plan = { NULL, NULL };

            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &source =
                    inObservation.nearbyObjects[i];

                if( source.requiredToolID > 0 &&
                    source.toolFoodResultID > 0 &&
                    ( plan.source == NULL ||
                      source.distance < plan.source->distance ) ) {
                    plan.source = &source;
                }
            }

            if( plan.source == NULL ) {
                return plan;
            }

            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &tool =
                    inObservation.nearbyObjects[i];

                if( tool.objectID == plan.source->requiredToolID &&
                    tool.pickupable &&
                    ( plan.tool == NULL ||
                      tool.distance < plan.tool->distance ) ) {
                    plan.tool = &tool;
                }
            }

            return plan;
        }

        const VisibleObject *findWanderTarget(
            const AgentObservation &inObservation ) const {
            const VisibleObject *best = NULL;

            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];

                if( o.distance <= 2 ) {
                    continue;
                }

                if( o.x == mLastTargetX && o.y == mLastTargetY &&
                    inObservation.currentTime - mLastActionTime < 5.0 ) {
                    continue;
                }

                if( best == NULL || o.distance < best->distance ) {
                    best = &o;
                }
            }
            return best;
        }

        const char *actionName( AgentActionType inType ) const {
            switch( inType ) {
                case AgentActionType::MOVE_TO: return "MOVE_TO";
                case AgentActionType::INTERACT: return "INTERACT";
                case AgentActionType::EAT: return "EAT";
                case AgentActionType::DROP: return "DROP";
                default: return "NONE";
            }
        }

        void printDebug( const AgentObservation &inObservation ) {
            if( inObservation.currentTime < mNextDebugTime ) {
                return;
            }

            std::printf(
                "AGENT STATE: x=%d y=%d age=%.2f food=%d/%d "
                "holding=%d heldFood=%d moving=%d visible=%zu\n",
                inObservation.x,
                inObservation.y,
                inObservation.age,
                inObservation.foodStore,
                inObservation.foodCapacity,
                inObservation.heldObjectID,
                inObservation.heldObjectFoodValue,
                inObservation.inMotion ? 1 : 0,
                inObservation.nearbyObjects.size() );

            mNextDebugTime = inObservation.currentTime + 3.0;
        }
};

#endif