#ifndef AGENT_EVENT_LOGGER_INCLUDED
#define AGENT_EVENT_LOGGER_INCLUDED

#include <cstdio>
#include <cstdlib>
#include <cstring>

// Lightweight JSONL instrumentation for BasicAgent.
//
// This logger deliberately does not alter agent decisions.  It records the
// observations and actions needed for later object-belief and expectation
// learning.  Logging is enabled by default and can be disabled with:
//
//     export OHOL_AGENT_LOG_ENABLED=0
//
// The output path can be changed with:
//
//     export OHOL_AGENT_LOG_PATH=/tmp/agent-events.jsonl
//
// The default path is agent-events.jsonl in the client's working directory.
class AgentEventLogger {
    public:
        AgentEventLogger()
            : mFile( NULL ),
              mEnabled( true ),
              mSequence( 0 ),
              mLastHeldObjectID( 0 ),
              mLastFoodStore( 0 ),
              mLastX( 0 ),
              mLastY( 0 ),
              mHavePreviousObservation( false ),
              mPendingAction( false ),
              mPendingActionType( AgentActionType::NONE ),
              mPendingTargetX( 0 ),
              mPendingTargetY( 0 ),
              mPendingIssuedAt( 0.0 ) {

            const char *enabled = std::getenv( "OHOL_AGENT_LOG_ENABLED" );
            if( enabled != NULL && std::strcmp( enabled, "0" ) == 0 ) {
                mEnabled = false;
                return;
            }

            const char *path = std::getenv( "OHOL_AGENT_LOG_PATH" );
            if( path == NULL || path[0] == '\0' ) {
                path = "agent-events.jsonl";
            }

            mFile = std::fopen( path, "a" );
            if( mFile == NULL ) {
                mEnabled = false;
                std::fprintf(
                    stderr,
                    "AGENT LOGGER: failed to open %s; logging disabled\n",
                    path );
                return;
            }

            std::setvbuf( mFile, NULL, _IOLBF, 0 );
            std::fprintf(
                mFile,
                "{\"event\":\"logger_started\",\"schema_version\":1}\n" );
        }

        ~AgentEventLogger() {
            if( mFile != NULL ) {
                std::fprintf(
                    mFile,
                    "{\"event\":\"logger_stopped\",\"sequence\":%lu}\n",
                    mSequence );
                std::fclose( mFile );
            }
        }

        void reset() {
            mLastHeldObjectID = 0;
            mLastFoodStore = 0;
            mLastX = 0;
            mLastY = 0;
            mHavePreviousObservation = false;
            mPendingAction = false;

            writeSimpleEvent( "life_reset" );
        }

        void observe( const AgentObservation &inObservation ) {
            if( !mEnabled || mFile == NULL ) {
                return;
            }

            if( mPendingAction ) {
                writeOutcome( inObservation );
                mPendingAction = false;
            }

            std::fprintf(
                mFile,
                "{\"event\":\"observation\","
                "\"sequence\":%lu,"
                "\"time\":%.6f,"
                "\"age\":%.6f,"
                "\"x\":%d,\"y\":%d,"
                "\"held_object_id\":%d,"
                "\"held_food_value\":%d,"
                "\"food_store\":%d,"
                "\"food_capacity\":%d,"
                "\"max_food_store\":%d,"
                "\"max_food_capacity\":%d,"
                "\"in_motion\":%s,"
                "\"visible_count\":%lu,"
                "\"visible_objects\":[",
                nextSequence(),
                inObservation.currentTime,
                inObservation.age,
                inObservation.x,
                inObservation.y,
                inObservation.heldObjectID,
                inObservation.heldObjectFoodValue,
                inObservation.foodStore,
                inObservation.foodCapacity,
                inObservation.maxFoodStore,
                inObservation.maxFoodCapacity,
                inObservation.inMotion ? "true" : "false",
                (unsigned long)inObservation.nearbyObjects.size() );

            for( size_t i=0;
                 i<inObservation.nearbyObjects.size();
                 i++ ) {

                const VisibleObject &object =
                    inObservation.nearbyObjects[i];

                if( i > 0 ) {
                    std::fputc( ',', mFile );
                }

                std::fprintf(
                    mFile,
                    "{\"object_id\":%d,"
                    "\"x\":%d,\"y\":%d,"
                    "\"distance\":%d,"
                    "\"food_value\":%d,"
                    "\"pickupable\":%s,"
                    "\"empty_hand_result_id\":%d,"
                    "\"required_tool_id\":%d,"
                    "\"tool_result_id\":%d}",
                    object.objectID,
                    object.x,
                    object.y,
                    object.distance,
                    object.foodValue,
                    object.pickupable ? "true" : "false",
                    object.emptyHandFoodResultID,
                    object.requiredToolID,
                    object.toolFoodResultID );
            }

            std::fprintf( mFile, "]}\n" );

            mLastHeldObjectID = inObservation.heldObjectID;
            mLastFoodStore = inObservation.foodStore;
            mLastX = inObservation.x;
            mLastY = inObservation.y;
            mHavePreviousObservation = true;
        }

        void action(
            AgentActionType inType,
            int inTargetX,
            int inTargetY,
            double inTime,
            const char *inReason ) {

            if( !mEnabled || mFile == NULL ) {
                return;
            }

            std::fprintf(
                mFile,
                "{\"event\":\"action\","
                "\"sequence\":%lu,"
                "\"time\":%.6f,"
                "\"action\":\"%s\","
                "\"target_x\":%d,\"target_y\":%d,"
                "\"reason\":\"%s\"}\n",
                nextSequence(),
                inTime,
                actionName( inType ),
                inTargetX,
                inTargetY,
                inReason == NULL ? "" : inReason );

            mPendingAction = true;
            mPendingActionType = inType;
            mPendingTargetX = inTargetX;
            mPendingTargetY = inTargetY;
            mPendingIssuedAt = inTime;
        }

    private:
        FILE *mFile;
        bool mEnabled;
        unsigned long mSequence;

        int mLastHeldObjectID;
        int mLastFoodStore;
        int mLastX;
        int mLastY;
        bool mHavePreviousObservation;

        bool mPendingAction;
        AgentActionType mPendingActionType;
        int mPendingTargetX;
        int mPendingTargetY;
        double mPendingIssuedAt;

        unsigned long nextSequence() {
            mSequence++;
            return mSequence;
        }

        void writeSimpleEvent( const char *inEvent ) {
            if( !mEnabled || mFile == NULL ) {
                return;
            }
            std::fprintf(
                mFile,
                "{\"event\":\"%s\",\"sequence\":%lu}\n",
                inEvent,
                nextSequence() );
        }

        void writeOutcome( const AgentObservation &inObservation ) {
            std::fprintf(
                mFile,
                "{\"event\":\"action_outcome\","
                "\"sequence\":%lu,"
                "\"time\":%.6f,"
                "\"issued_at\":%.6f,"
                "\"action\":\"%s\","
                "\"target_x\":%d,\"target_y\":%d,"
                "\"position_changed\":%s,"
                "\"held_before\":%d,\"held_after\":%d,"
                "\"food_before\":%d,\"food_after\":%d,"
                "\"held_changed\":%s,"
                "\"food_increased\":%s}\n",
                nextSequence(),
                inObservation.currentTime,
                mPendingIssuedAt,
                actionName( mPendingActionType ),
                mPendingTargetX,
                mPendingTargetY,
                ( !mHavePreviousObservation ||
                  inObservation.x != mLastX ||
                  inObservation.y != mLastY ) ? "true" : "false",
                mLastHeldObjectID,
                inObservation.heldObjectID,
                mLastFoodStore,
                inObservation.foodStore,
                ( !mHavePreviousObservation ||
                  inObservation.heldObjectID !=
                      mLastHeldObjectID ) ? "true" : "false",
                ( mHavePreviousObservation &&
                  inObservation.foodStore >
                      mLastFoodStore ) ? "true" : "false" );
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
};

#endif
