#ifndef BASIC_AGENT_INCLUDED
#define BASIC_AGENT_INCLUDED

#include <cstdio>
#include <cstdlib>
#include <vector>


struct VisibleObject {

    int objectID;
    int x;
    int y;
    int distance;
};


struct AgentObservation {

    int x;
    int y;

    int heldObjectID;

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
    MOVE_TO
    // future milestones:
    // INTERACT,
    // EAT,
    // DROP
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
              mLastTargetX( 0 ),
              mLastTargetY( 0 ),
              mHasLastTarget( false ),
              mLastTargetIssueTime( 0.0 ) {
        }


        AgentAction decide( const AgentObservation &inObservation ) {

            AgentAction action;
            action.type = AgentActionType::NONE;
            action.targetX = 0;
            action.targetY = 0;

            if( !mEnabled ) {
                return action;
            }

            printDebug( inObservation );

            if( inObservation.inMotion ) {
                // still walking, don't interrupt ourselves
                return action;
            }

            if( inObservation.nearbyObjects.empty() ) {
                // nothing visible, nothing to do (yet)
                return action;
            }

            // target the nearest object we have NOT already reached
            // (skip objects at distance <= 1 -- we're already adjacent
            //  to those; milestone 4 will INTERACT with them instead)
            const VisibleObject *nearest =
                findNearestBeyond( inObservation, 1 );

            if( nearest == NULL ) {
                // everything visible is already adjacent
                return action;
            }

            if( mHasLastTarget &&
                nearest->x == mLastTargetX &&
                nearest->y == mLastTargetY &&
                inObservation.currentTime - mLastTargetIssueTime < 5.0 ) {
                // we recently issued a move to this exact target and
                // we're stationary again without having reached it
                // (unreachable, or path truncated)
                // don't spam re-requests for 5 seconds
                return action;
            }

            action.type = AgentActionType::MOVE_TO;
            action.targetX = nearest->x;
            action.targetY = nearest->y;

            mLastTargetX = nearest->x;
            mLastTargetY = nearest->y;
            mHasLastTarget = true;
            mLastTargetIssueTime = inObservation.currentTime;

            printf(
                "AGENT ACTION: MOVE_TO x=%d y=%d (target id=%d distance=%d)\n",
                nearest->x,
                nearest->y,
                nearest->objectID,
                nearest->distance );

            return action;
        }


        // kept for compatibility / passive observation
        void observe( const AgentObservation &inObservation ) {

            if( !mEnabled ) {
                return;
            }

            printDebug( inObservation );
        }


        void setEnabled( bool inEnabled ) {
            mEnabled = inEnabled;
        }


        // call on new life / rebirth so stale state doesn't
        // suppress behavior in the next life
        void reset() {
            mNextDebugTime = 0.0;
            mHasLastTarget = false;
            mLastTargetX = 0;
            mLastTargetY = 0;
            mLastTargetIssueTime = 0.0;
        }


    private:

        bool mEnabled;
        double mNextDebugTime;

        int mLastTargetX;
        int mLastTargetY;
        bool mHasLastTarget;
        double mLastTargetIssueTime;


        const VisibleObject *findNearest(
            const AgentObservation &inObservation ) {

            if( inObservation.nearbyObjects.empty() ) {
                return NULL;
            }

            const VisibleObject *nearest =
                &inObservation.nearbyObjects[0];

            for( size_t i = 1;
                 i < inObservation.nearbyObjects.size();
                 i++ ) {

                const VisibleObject &candidate =
                    inObservation.nearbyObjects[i];

                if( candidate.distance < nearest->distance ) {
                    nearest = &candidate;
                }
            }

            return nearest;
        }


        // nearest object with distance strictly greater than inMinDistance
        // returns NULL if none qualify
        const VisibleObject *findNearestBeyond(
            const AgentObservation &inObservation,
            int inMinDistance ) {

            const VisibleObject *nearest = NULL;

            for( size_t i = 0;
                 i < inObservation.nearbyObjects.size();
                 i++ ) {

                const VisibleObject &candidate =
                    inObservation.nearbyObjects[i];

                if( candidate.distance <= inMinDistance ) {
                    continue;
                }

                if( nearest == NULL ||
                    candidate.distance < nearest->distance ) {
                    nearest = &candidate;
                }
            }

            return nearest;
        }


        void printDebug( const AgentObservation &inObservation ) {

            if( inObservation.currentTime < mNextDebugTime ) {
                return;
            }

            printf(
                "AGENT STATE: "
                "x=%d y=%d "
                "age=%.2f "
                "food=%d/%d "
                "holding=%d "
                "moving=%d "
                "visibleObjects=%zu\n",
                inObservation.x,
                inObservation.y,
                inObservation.age,
                inObservation.foodStore,
                inObservation.foodCapacity,
                inObservation.heldObjectID,
                inObservation.inMotion ? 1 : 0,
                inObservation.nearbyObjects.size() );

            if( inObservation.nearbyObjects.empty() ) {
                printf( "AGENT TARGET: none\n" );
            }
            else {
                const VisibleObject *nearest =
                    findNearest( inObservation );

                printf(
                    "AGENT TARGET: id=%d x=%d y=%d distance=%d\n",
                    nearest->objectID,
                    nearest->x,
                    nearest->y,
                    nearest->distance );
            }

            mNextDebugTime =
                inObservation.currentTime + 3.0;
        }
};


#endif