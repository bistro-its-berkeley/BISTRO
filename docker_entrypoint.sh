#!/bin/bash

##################################################################
# Init any required service(s)
##################################################################
# no-op

##################################################################
# Execute the actual simulation
# Note : The paths specified here is relative to the docker
# container. And this entrypoint is expected to be executed inside
# the docker container.
##################################################################
/competitions/bin/competitions $@

##################################################################
# Post Processing / Cleanup
##################################################################
# No-Op
echo "Post Processing / Cleanup complete"

if [ -n "${AICROWD_IS_GRADING}" ]; then
  sleep 600
  # Sleep for 10 minutes while waiting for the evaluator to 
  # do the necessary cleanup
fi
