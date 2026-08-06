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

#include "AgentEventLogger.h"

class BasicAgent {
    public:
        BasicAgent()
            : mEnabled( true ),
              mNextDebugTime( 0.0 ),
              mLastActionTime( -100.0 ),
              mLastTargetX( 0 ),
              mLastTargetY( 0 ),
              mInteractionAttempts( 0 ),
              mLastInteractionTime( -100.0 ),
              mPendingFoodSource( false ),
              mPendingFoodSourceX( 0 ),
              mPendingFoodSourceY( 0 ),
              mPendingFoodSourceTime( -100.0 ),
              mConfirmedReturnActive( false ),
              mConfirmedReturnX( 0 ),
              mConfirmedReturnY( 0 ),
              mConfirmedReturnBestDistanceSquared( 0 ),
              mConfirmedReturnLastProgressTime( -100.0 ),
              mEatAwaitingResult( false ),
              mEatHeldObjectID( 0 ),
              mEatFoodStore( 0 ),
              mEatRetryTime( -100.0 ),
              mDropHeldObjectID( 0 ),
              mDropTargetX( 0 ),
                  mDropTargetY( 0 ),
                  mDropAttempts( 0 ),
                  mDropRetryTime( -100.0 ),
                  mPreviousHeldObjectID( 0 ),
                  mToolParkPending( false ),
                  mToolWaiting( false ),
                  mToolX( 0 ),
                  mToolY( 0 ),
                  mHasBase( false ),
                  mBaseX( 0 ),
                  mBaseY( 0 ),
                  mBaseScore( -100000 ),
                  mBaseCandidateX( 0 ),
                  mBaseCandidateY( 0 ),
                  mBaseCandidateScore( -100000 ),
                  mBaseCandidateObservations( 0 ) {
        }

        AgentAction decide( const AgentObservation &inObservation ) {
            AgentAction none = makeAction( AgentActionType::NONE, 0, 0 );

            if( !mEnabled ) {
                return none;
            }

                mEventLogger.observe( inObservation );

                printDebug( inObservation );
                updateFoodSourceOutcome( inObservation );
                updateEatOutcome( inObservation );
                updateToolOutcome( inObservation );
                updateBaseCandidate( inObservation );
                bool confirmedReturnStalled =
                    updateConfirmedReturnProgress( inObservation );

            // A stalled remembered-source path must be interruptible.  For
            // ordinary movement, retain the existing wait-until-stopped rule.
            if( ( inObservation.inMotion && !confirmedReturnStalled ) ||
                inObservation.currentTime - mLastActionTime < 0.35 ) {
                return none;
            }

                bool hungry =
                    inObservation.foodStore <=
                    ( inObservation.foodCapacity * 2 ) / 3;

            if( hungry ) {
                if( inObservation.heldObjectID > 0 &&
                    inObservation.heldObjectFoodValue > 0 ) {
                    if( mEatAwaitingResult ) {
                        return none;
                    }
                    beginEatAttempt( inObservation );
                    return issue( AgentActionType::EAT,
                                  inObservation.x,
                                  inObservation.y,
                                  inObservation.currentTime,
                                  "held food" );
                }

                // A rejected DROP must not monopolize survival forever.
                // During the cooldown, keep moving and looking for a better
                // location instead of retrying the same server command.
                    if( inObservation.heldObjectID != 0 &&
                        inObservation.currentTime < mDropRetryTime ) {
                    const VisibleObject *escape =
                        findWanderTarget( inObservation );
                    if( escape != NULL ) {
                        rememberWanderTarget(
                            *escape, inObservation.currentTime );
                        return issue( AgentActionType::MOVE_TO,
                                      escape->x,
                                      escape->y,
                                      inObservation.currentTime,
                                      "failed-drop escape" );
                    }
                        return none;
                    }

                    if( inObservation.heldObjectID == 34 ) {
                        return parkSharpStone( inObservation );
                    }

                // Prefer a location that previously produced food.
                // We remember the INTERACT target, not the player's later
                // position, and only confirm it after food appears in hand.
                if( inObservation.heldObjectID == 0 ) {
                    const ConfirmedFoodSource *confirmed =
                        findNearestConfirmedFoodSource( inObservation );
                    if( confirmed != NULL ) {
                        return approachConfirmedFoodSource(
                            *confirmed, inObservation );
                    }
                }

                const VisibleObject *looseFood =
                    findNearestLooseFood( inObservation );

                if( looseFood != NULL ) {
                    if( inObservation.heldObjectID != 0 ) {
                        return dropHeldObject( inObservation );
                    }
                    return approachOrInteract(
                        *looseFood, inObservation, "loose food" );
                }

                const VisibleObject *bareSource =
                    findNearestBareHandSource( inObservation );

                if( bareSource != NULL ) {
                    if( inObservation.heldObjectID != 0 ) {
                        return dropHeldObject( inObservation );
                    }
                    return approachOrInteract(
                        *bareSource,
                        inObservation,
                        "empty-hand food source" );
                }

                ToolPlan plan = findNearestToolPlan( inObservation );

                if( plan.source != NULL &&
                    inObservation.heldObjectID ==
                    plan.source->requiredToolID ) {
                    return approachOrInteract(
                        *plan.source,
                        inObservation,
                        "tool food source" );
                }

                if( plan.source != NULL && plan.tool != NULL ) {
                    if( inObservation.heldObjectID != 0 ) {
                        return dropHeldObject( inObservation );
                    }
                    return approachOrInteract(
                        *plan.tool,
                        inObservation,
                        "required food tool" );
                }
            }

            // This block must be outside the hungry branch above.  The previous
            // version nested `if( !hungry )` inside `if( hungry )`, making all
            // Sharp Stone behavior unreachable.
            if( !hungry ) {
                // Recover a parked Sharp Stone before starting another one.
                if( inObservation.heldObjectID == 0 && mToolWaiting ) {
                    const VisibleObject *parked =
                        findParkedSharpStone( inObservation );
                    if( parked != NULL ) {
                        return approachOrInteract(
                            *parked,
                            inObservation,
                            "recover parked sharp stone" );
                    }
                }

                // Stone (33) + Big Hard Rock (32) -> Sharp Stone (34).
                const VisibleObject *bigRock =
                    findNearestObject( inObservation, 32, false );

                if( inObservation.heldObjectID == 33 &&
                    bigRock != NULL ) {
                    return approachOrInteract(
                        *bigRock,
                        inObservation,
                        "craft sharp stone" );
                }

                // Pick up a Stone even when the Big Hard Rock is not currently
                // visible.  The agent can carry it while exploring until it
                // encounters the crafting rock.
                if( inObservation.heldObjectID == 0 ) {
                    const VisibleObject *stone =
                        findNearestObject( inObservation, 33, true );
                    if( stone != NULL ) {
                        return approachOrInteract(
                            *stone,
                            inObservation,
                            "pick up stone for crafting" );
                    }
                }
            }

            const VisibleObject *wander = NULL;
            bool criticalHunger =
                inObservation.foodStore <= 8;

            if( criticalHunger ) {
                wander = findLocalForageTarget( inObservation );
            }
            else {
                wander = findWanderTarget( inObservation );
            }

            if( wander != NULL ) {
                rememberWanderTarget(
                    *wander, inObservation.currentTime );
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
                mEventLogger.observe( inObservation );
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
            mVisitedTargets.clear();
            mBlockedTargets.clear();
            mConfirmedFoodSources.clear();
            mInteractionAttempts = 0;
            mLastInteractionTime = -100.0;
            mPendingFoodSource = false;
            mPendingFoodSourceTime = -100.0;
            mConfirmedReturnActive = false;
            mConfirmedReturnX = 0;
            mConfirmedReturnY = 0;
            mConfirmedReturnBestDistanceSquared = 0;
            mConfirmedReturnLastProgressTime = -100.0;
            mEatAwaitingResult = false;
            mEatRetryTime = -100.0;
            mDropHeldObjectID = 0;
            mDropTargetX = 0;
            mDropTargetY = 0;
            mDropAttempts = 0;
            mDropRetryTime = -100.0;
            mPreviousHeldObjectID = 0;
            mToolParkPending = false;
            mToolWaiting = false;
            mToolX = 0;
            mToolY = 0;
            mHasBase = false;
            mBaseX = 0;
            mBaseY = 0;
            mBaseScore = -100000;
            mBaseCandidateX = 0;
            mBaseCandidateY = 0;
            mBaseCandidateScore = -100000;
            mBaseCandidateObservations = 0;
            mEventLogger.reset();
        }

    private:
        struct ToolPlan {
            const VisibleObject *source;
            const VisibleObject *tool;
        };

        struct VisitedTarget {
            int x;
            int y;
            double expiresAt;
        };

        struct BlockedTarget {
            int x;
            int y;
            double expiresAt;
        };

        struct ConfirmedFoodSource {
            int x;
            int y;
        };

        bool mEnabled;
        double mNextDebugTime;
        double mLastActionTime;
        int mLastTargetX;
        int mLastTargetY;
        std::vector<VisitedTarget> mVisitedTargets;
        std::vector<BlockedTarget> mBlockedTargets;
        int mInteractionAttempts;
        int mLastInteractionX;
        int mLastInteractionY;
        double mLastInteractionTime;
        bool mPendingFoodSource;
        int mPendingFoodSourceX;
        int mPendingFoodSourceY;
        double mPendingFoodSourceTime;
        std::vector<ConfirmedFoodSource> mConfirmedFoodSources;
        bool mConfirmedReturnActive;
        int mConfirmedReturnX;
        int mConfirmedReturnY;
        int mConfirmedReturnBestDistanceSquared;
        double mConfirmedReturnLastProgressTime;
        bool mEatAwaitingResult;
        int mEatHeldObjectID;
        int mEatFoodStore;
        double mEatRetryTime;
        int mDropHeldObjectID;
        int mDropTargetX;
        int mDropTargetY;
        int mDropAttempts;
        double mDropRetryTime;
        int mPreviousHeldObjectID;
        bool mToolParkPending;
        bool mToolWaiting;
        int mToolX;
        int mToolY;
        bool mHasBase;
        int mBaseX;
        int mBaseY;
        int mBaseScore;
        int mBaseCandidateX;
        int mBaseCandidateY;
        int mBaseCandidateScore;
        int mBaseCandidateObservations;
        AgentEventLogger mEventLogger;

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

            mEventLogger.action(
                inType,
                inX,
                inY,
                inTime,
                inReason );

            std::printf(
                "AGENT ACTION: %s x=%d y=%d reason=%s\n",
                actionName( inType ), inX, inY, inReason );

            return makeAction( inType, inX, inY );
        }

        AgentAction approachOrInteract(
            const VisibleObject &inTarget,
            const AgentObservation &inObservation,
            const char *inReason ) {
            int deltaX = inObservation.x - inTarget.x;
            int deltaY = inObservation.y - inTarget.y;

            if( deltaX < 0 ) {
                deltaX = -deltaX;
            }
            if( deltaY < 0 ) {
                deltaY = -deltaY;
            }

            // OneLife ground objects are used from a cardinally adjacent tile.
            // Never walk onto the object's own tile before interacting.
            if( deltaX + deltaY <= 1 ) {
                recordInteractionAttempt(
                    inTarget.x,
                    inTarget.y,
                    inObservation.currentTime );
                return issue( AgentActionType::INTERACT,
                              inTarget.x,
                              inTarget.y,
                              inObservation.currentTime,
                              inReason );
            }

            static const int offsets[4][2] = {
                { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }
            };

            int approachX = inTarget.x;
            int approachY = inTarget.y;
            int bestDistanceSquared = 0x7FFFFFFF;
            bool foundApproach = false;

            for( int i=0; i<4; i++ ) {
                int candidateX = inTarget.x + offsets[i][0];
                int candidateY = inTarget.y + offsets[i][1];

                if( hasObjectAt(
                        inObservation, candidateX, candidateY ) ) {
                    continue;
                }

                int dx = candidateX - inObservation.x;
                int dy = candidateY - inObservation.y;
                int distanceSquared = dx * dx + dy * dy;

                if( !foundApproach ||
                    distanceSquared < bestDistanceSquared ) {
                    foundApproach = true;
                    bestDistanceSquared = distanceSquared;
                    approachX = candidateX;
                    approachY = candidateY;
                }
            }

            if( !foundApproach ) {
                std::printf(
                    "AGENT NO APPROACH TILE: target=%d x=%d y=%d reason=%s\n",
                    inTarget.objectID,
                    inTarget.x,
                    inTarget.y,
                    inReason );
                return makeAction( AgentActionType::NONE, 0, 0 );
            }

            return issue( AgentActionType::MOVE_TO,
                          approachX,
                          approachY,
                          inObservation.currentTime,
                          inReason );
        }

        AgentAction dropHeldObject(
            const AgentObservation &inObservation ) {
            static const int offsets[4][2] = {
                { 1, 0 }, { -1, 0 }, { 0, 1 }, { 0, -1 }
            };

            // A changed held-object ID proves that the previous drop either
            // succeeded or the inventory changed for another reason.
            if( inObservation.heldObjectID != mDropHeldObjectID ) {
                mDropHeldObjectID = inObservation.heldObjectID;
                mDropAttempts = 0;
                mDropRetryTime = -100.0;
            }

            for( int i=0; i<4; i++ ) {
                int x = inObservation.x + offsets[i][0];
                int y = inObservation.y + offsets[i][1];

                if( !hasObjectAt( inObservation, x, y ) ) {
                    if( mDropAttempts > 0 &&
                        ( x != mDropTargetX || y != mDropTargetY ) ) {
                        mDropAttempts = 0;
                    }

                    mDropTargetX = x;
                    mDropTargetY = y;

                    if( mDropAttempts >= 3 ) {
                        mDropAttempts = 0;
                        mDropRetryTime =
                            inObservation.currentTime + 8.0;
                        std::printf(
                            "AGENT DROP BLOCKED: held=%d seconds=8 reason=no outcome\n",
                            inObservation.heldObjectID );
                        return makeAction(
                            AgentActionType::NONE, 0, 0 );
                    }

                    mDropAttempts++;
                    return issue( AgentActionType::DROP,
                                  x,
                                  y,
                                  inObservation.currentTime,
                                  "clear hand" );
                }
            }

            // No adjacent empty tile: pause dropping briefly and allow the
            // decision loop to choose an exploration move next time.
            mDropAttempts = 0;
            mDropRetryTime = inObservation.currentTime + 3.0;
            return makeAction( AgentActionType::NONE, 0, 0 );
        }

        AgentAction parkSharpStone(
            const AgentObservation &inObservation ) {
            AgentAction action = dropHeldObject( inObservation );
            if( action.type == AgentActionType::DROP ) {
                mToolParkPending = true;
                mToolX = action.targetX;
                mToolY = action.targetY;
                std::printf(
                    "AGENT TOOL PARK: x=%d y=%d\n",
                    mToolX, mToolY );
            }
            return action;
        }

        void updateToolOutcome(
            const AgentObservation &inObservation ) {
            if( mToolParkPending &&
                mPreviousHeldObjectID == 34 &&
                inObservation.heldObjectID != 34 ) {
                mToolWaiting = true;
                mToolParkPending = false;
                std::printf(
                    "AGENT TOOL PARKED: x=%d y=%d\n",
                    mToolX, mToolY );
            }

            if( inObservation.heldObjectID == 34 ) {
                if( mToolWaiting ) {
                    std::printf( "AGENT TOOL RECOVERED\n" );
                }
                mToolWaiting = false;
                mToolParkPending = false;
            }

            // If a pending DROP produced no inventory change, allow the
            // normal drop retry logic to try again.
            if( mToolParkPending &&
                inObservation.currentTime - mLastActionTime > 2.0 &&
                inObservation.heldObjectID == 34 ) {
                mToolParkPending = false;
            }

            mPreviousHeldObjectID = inObservation.heldObjectID;
        }

        const VisibleObject *findParkedSharpStone(
            const AgentObservation &inObservation ) const {
            const VisibleObject *fallback = NULL;
            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];
                if( o.objectID != 34 || !o.pickupable ) {
                    continue;
                }
                if( o.x == mToolX && o.y == mToolY ) {
                    return &o;
                }
                if( fallback == NULL ||
                    o.distance < fallback->distance ) {
                    fallback = &o;
                }
            }
            return fallback;
        }

        const VisibleObject *findNearestObject(
            const AgentObservation &inObservation,
            int inObjectID,
            bool inRequirePickupable ) const {
            const VisibleObject *best = NULL;
            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];
                if( o.objectID != inObjectID ||
                    ( inRequirePickupable && !o.pickupable ) ||
                    isBlocked( o.x, o.y, inObservation.currentTime ) ) {
                    continue;
                }
                if( best == NULL || o.distance < best->distance ) {
                    best = &o;
                }
            }
            return best;
        }

        void updateBaseCandidate(
            const AgentObservation &inObservation ) {
            int foodResources = 0;
            int stones = 0;
            int bigRocks = 0;
            int mosquitoes = 0;

            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];
                if( o.distance > 12 ) {
                    continue;
                }
                if( o.foodValue > 0 ||
                    o.emptyHandFoodResultID > 0 ||
                    o.toolFoodResultID > 0 ) {
                    foodResources++;
                }
                if( o.objectID == 33 ) {
                    stones++;
                }
                else if( o.objectID == 32 ) {
                    bigRocks++;
                }
                else if( o.objectID == 2156 ) {
                    mosquitoes++;
                }
            }

            // A useful first base is a safe resource hub, not a building.
            // A Big Hard Rock is mandatory because it anchors tool crafting.
            if( bigRocks == 0 || foodResources < 2 || mosquitoes > 0 ) {
                return;
            }

            int score =
                foodResources * 4 +
                ( stones > 2 ? 2 : stones ) * 2 +
                bigRocks * 3;

            int dx = inObservation.x - mBaseCandidateX;
            int dy = inObservation.y - mBaseCandidateY;
            bool sameArea =
                mBaseCandidateObservations > 0 &&
                dx * dx + dy * dy <= 16;

            if( !sameArea || score > mBaseCandidateScore + 2 ) {
                mBaseCandidateX = inObservation.x;
                mBaseCandidateY = inObservation.y;
                mBaseCandidateScore = score;
                mBaseCandidateObservations = 1;
                return;
            }

            mBaseCandidateObservations++;
            if( mBaseCandidateObservations >= 3 &&
                ( !mHasBase || score > mBaseScore + 3 ) ) {
                mHasBase = true;
                mBaseX = mBaseCandidateX;
                mBaseY = mBaseCandidateY;
                mBaseScore = mBaseCandidateScore;
                std::printf(
                    "AGENT BASE SELECTED: x=%d y=%d score=%d "
                    "food=%d stones=%d rocks=%d\n",
                    mBaseX, mBaseY, mBaseScore,
                    foodResources, stones, bigRocks );
            }
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
                    !isBlocked( o.x, o.y, inObservation.currentTime ) &&
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
                    !isBlocked( o.x, o.y, inObservation.currentTime ) &&
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
                    !isBlocked( source.x, source.y,
                                inObservation.currentTime ) &&
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
                    !isBlocked( tool.x, tool.y,
                                inObservation.currentTime ) &&
                    ( plan.tool == NULL ||
                      tool.distance < plan.tool->distance ) ) {
                    plan.tool = &tool;
                }
            }

            return plan;
        }

        bool isBlocked(
            int inX, int inY, double inTime ) const {
            for( size_t i=0; i<mBlockedTargets.size(); i++ ) {
                const BlockedTarget &blocked = mBlockedTargets[i];
                if( blocked.expiresAt > inTime &&
                    blocked.x == inX && blocked.y == inY ) {
                    return true;
                }
            }
            return false;
        }

        void recordInteractionAttempt(
            int inX, int inY, double inTime ) {
            std::vector<BlockedTarget> active;
            for( size_t i=0; i<mBlockedTargets.size(); i++ ) {
                if( mBlockedTargets[i].expiresAt > inTime ) {
                    active.push_back( mBlockedTargets[i] );
                }
            }
            mBlockedTargets.swap( active );

            if( mInteractionAttempts > 0 &&
                mLastInteractionX == inX &&
                mLastInteractionY == inY &&
                inTime - mLastInteractionTime < 8.0 ) {
                mInteractionAttempts++;
            }
            else {
                mInteractionAttempts = 1;
                mLastInteractionX = inX;
                mLastInteractionY = inY;
            }
            mLastInteractionTime = inTime;
            mPendingFoodSource = true;
            mPendingFoodSourceX = inX;
            mPendingFoodSourceY = inY;
            mPendingFoodSourceTime = inTime;

            if( mInteractionAttempts >= 3 ) {
                BlockedTarget blocked = { inX, inY, inTime + 120.0 };
                mBlockedTargets.push_back( blocked );
                mInteractionAttempts = 0;
                std::printf(
                    "AGENT BLOCKED TARGET: x=%d y=%d seconds=120 reason=no outcome\n",
                    inX, inY );
            }
        }

        void updateFoodSourceOutcome(
            const AgentObservation &inObservation ) {
            if( !mPendingFoodSource ) {
                return;
            }

            if( inObservation.heldObjectID > 0 &&
                inObservation.heldObjectFoodValue > 0 ) {
                bool known = false;
                for( size_t i=0; i<mConfirmedFoodSources.size(); i++ ) {
                    if( mConfirmedFoodSources[i].x == mPendingFoodSourceX &&
                        mConfirmedFoodSources[i].y == mPendingFoodSourceY ) {
                        known = true;
                        break;
                    }
                }
                if( !known ) {
                    ConfirmedFoodSource source = {
                        mPendingFoodSourceX, mPendingFoodSourceY
                    };
                    mConfirmedFoodSources.push_back( source );
                    std::printf(
                        "AGENT CONFIRMED FOOD SOURCE: x=%d y=%d\n",
                        source.x, source.y );
                }
                mPendingFoodSource = false;
                mInteractionAttempts = 0;
                return;
            }

            if( inObservation.currentTime - mPendingFoodSourceTime >= 3.0 ) {
                mPendingFoodSource = false;
            }
        }

        const ConfirmedFoodSource *findNearestConfirmedFoodSource(
            const AgentObservation &inObservation ) const {
            const ConfirmedFoodSource *best = NULL;
            int bestDistanceSquared = 0;

            for( size_t i=0; i<mConfirmedFoodSources.size(); i++ ) {
                const ConfirmedFoodSource &source =
                    mConfirmedFoodSources[i];
                if( isBlocked( source.x, source.y,
                               inObservation.currentTime ) ) {
                    continue;
                }
                int dx = source.x - inObservation.x;
                int dy = source.y - inObservation.y;
                int distanceSquared = dx * dx + dy * dy;

                // With almost no food left, a long remembered-source trip is
                // more dangerous than searching the local visible area.
                if( inObservation.foodStore <= 4 &&
                    distanceSquared > 144 ) {
                    continue;
                }

                if( best == NULL ||
                    distanceSquared < bestDistanceSquared ) {
                    best = &source;
                    bestDistanceSquared = distanceSquared;
                }
            }
            return best;
        }

        AgentAction approachConfirmedFoodSource(
            const ConfirmedFoodSource &inSource,
            const AgentObservation &inObservation ) {
            int dx = inSource.x - inObservation.x;
            int dy = inSource.y - inObservation.y;

            // The source tile is commonly occupied.  Asking MOVE_TO to reach
            // that exact tile can produce a truncated path on the wrong side
            // of the object and then be reissued forever.  Once nearby, hand
            // the target to the normal INTERACT path; it approaches to the
            // object's valid use distance before sending USE.
            int distanceSquared = dx * dx + dy * dy;
            if( distanceSquared <= 16 ) {
                mConfirmedReturnActive = false;
                recordInteractionAttempt(
                    inSource.x, inSource.y, inObservation.currentTime );
                return issue( AgentActionType::INTERACT,
                              inSource.x,
                              inSource.y,
                              inObservation.currentTime,
                              "confirmed food source nearby" );
            }
            if( !mConfirmedReturnActive ||
                mConfirmedReturnX != inSource.x ||
                mConfirmedReturnY != inSource.y ) {
                mConfirmedReturnActive = true;
                mConfirmedReturnX = inSource.x;
                mConfirmedReturnY = inSource.y;
                mConfirmedReturnBestDistanceSquared = distanceSquared;
                mConfirmedReturnLastProgressTime =
                    inObservation.currentTime;
            }

            return issue( AgentActionType::MOVE_TO,
                          inSource.x,
                          inSource.y,
                          inObservation.currentTime,
                          "return to confirmed food source" );
        }

        bool updateConfirmedReturnProgress(
            const AgentObservation &inObservation ) {
            if( !mConfirmedReturnActive ) {
                return false;
            }

            int dx = mConfirmedReturnX - inObservation.x;
            int dy = mConfirmedReturnY - inObservation.y;
            int distanceSquared = dx * dx + dy * dy;

            if( distanceSquared < mConfirmedReturnBestDistanceSquared ) {
                mConfirmedReturnBestDistanceSquared = distanceSquared;
                mConfirmedReturnLastProgressTime =
                    inObservation.currentTime;
                return false;
            }

            if( inObservation.currentTime -
                mConfirmedReturnLastProgressTime < 2.5 ) {
                return false;
            }

            BlockedTarget blocked = {
                mConfirmedReturnX,
                mConfirmedReturnY,
                inObservation.currentTime + 30.0
            };
            mBlockedTargets.push_back( blocked );
            std::printf(
                "AGENT BLOCKED CONFIRMED SOURCE: x=%d y=%d "
                "seconds=30 reason=no movement progress\n",
                mConfirmedReturnX, mConfirmedReturnY );
            mConfirmedReturnActive = false;
            return true;
        }

        const VisibleObject *findLocalForageTarget(
            const AgentObservation &inObservation ) const {
            const VisibleObject *best = NULL;
            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];
                if( o.distance <= 2 || o.distance > 12 ||
                    isBlocked( o.x, o.y, inObservation.currentTime ) ||
                    isRecentlyVisited(
                        o.x, o.y, inObservation.currentTime ) ) {
                    continue;
                }
                if( best == NULL || o.distance < best->distance ) {
                    best = &o;
                }
            }
            return best;
        }

        void beginEatAttempt(
            const AgentObservation &inObservation ) {
            mEatAwaitingResult = true;
            mEatHeldObjectID = inObservation.heldObjectID;
            mEatFoodStore = inObservation.foodStore;
            mEatRetryTime = inObservation.currentTime + 2.0;
        }

        void updateEatOutcome(
            const AgentObservation &inObservation ) {
            if( !mEatAwaitingResult ) {
                return;
            }
            if( inObservation.heldObjectID != mEatHeldObjectID ||
                inObservation.foodStore > mEatFoodStore ||
                inObservation.currentTime >= mEatRetryTime ) {
                mEatAwaitingResult = false;
            }
        }

        bool isRecentlyVisited(
            int inX, int inY, double inTime ) const {
            for( size_t i=0; i<mVisitedTargets.size(); i++ ) {
                const VisitedTarget &visited = mVisitedTargets[i];
                if( visited.expiresAt <= inTime ) {
                    continue;
                }
                int dx = inX - visited.x;
                int dy = inY - visited.y;
                if( dx * dx + dy * dy <= 9 ) {
                    return true;
                }
            }
            return false;
        }

        void rememberWanderTarget(
            const VisibleObject &inTarget, double inTime ) {
            std::vector<VisitedTarget> activeTargets;
            for( size_t i=0; i<mVisitedTargets.size(); i++ ) {
                if( mVisitedTargets[i].expiresAt > inTime ) {
                    activeTargets.push_back( mVisitedTargets[i] );
                }
            }
            VisitedTarget visited = {
                inTarget.x, inTarget.y, inTime + 20.0
            };
            activeTargets.push_back( visited );
            mVisitedTargets.swap( activeTargets );
        }

        const VisibleObject *findWanderTarget(
            const AgentObservation &inObservation ) const {
            const VisibleObject *best = NULL;
            for( size_t i=0; i<inObservation.nearbyObjects.size(); i++ ) {
                const VisibleObject &o = inObservation.nearbyObjects[i];
                if( o.distance <= 2 ||
                    isRecentlyVisited(
                        o.x, o.y, inObservation.currentTime ) ) {
                    continue;
                }
                if( best == NULL || o.distance > best->distance ) {
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
                "holding=%d heldFood=%d moving=%d visible=%zu "
                "toolWaiting=%d base=%d,%d baseScore=%d\n",
                inObservation.x,
                inObservation.y,
                inObservation.age,
                inObservation.foodStore,
                inObservation.foodCapacity,
                inObservation.heldObjectID,
                inObservation.heldObjectFoodValue,
                inObservation.inMotion ? 1 : 0,
                inObservation.nearbyObjects.size(),
                mToolWaiting ? 1 : 0,
                mHasBase ? mBaseX : 0,
                mHasBase ? mBaseY : 0,
                mHasBase ? mBaseScore : -1 );

            mNextDebugTime = inObservation.currentTime + 3.0;
        }
};

#endif
