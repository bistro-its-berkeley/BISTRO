#!/usr/bin/env bash

sudo docker rm bistro-competition

POSITIONAL=()
while [[ $# -gt 0 ]]
do
key="$1"

case $key in
    -s|--scenario)
    SCENARIO="$2"
    shift # past argument
    shift # past value
    ;;
    -sz|--size)
    SIZE="$2"
    shift # past argument
    shift # past value
    ;;
    -m|--memory)
    MEMORY="$2"
    shift # past argument
    shift # past value
    ;;
    -c|--cpus)
    CPUS="$2"
    shift # past argument
    shift # past value
    ;;
    -i|--input)
          INPUT="$2"
          shift # past argument
          shift # past value
          ;;
   -n|--iters)
        ITERS="$2"
        shift # past argument
        shift # past value
              ;;
    *)    # unknown option
    POSITIONAL+=("$1") # save it in an array for later
    shift # past argument
    ;;
esac
done
set -- "${POSITIONAL[@]}" # restore positional parameters

echo INPUT = "${INPUT}"

for image in $(docker volume ls | awk -F' +' '{print $2}') ; do
    if [ ${image} == "competition-output" ]; then
        echo "Volume already exists"
    fi
done

if [ -z $(docker volume ls | awk -F' +' '{print $2}' | grep "competition-output") ]; then
    docker volume create competition-output >> /dev/null
fi


M_EXT=$(echo "${MEMORY}" | awk -F '([0-9])+' '{print $2}')
M_SIZE=$(echo "${MEMORY}" |  awk -F '[a-zA-Z]+' '{print $1}')

J_OPT=$(echo "\"-Xmx${M_SIZE}${M_EXT}\" \"-Xms$((M_SIZE/2))${M_EXT}\"")
JJ=$(echo JAVA_OPTS="${J_OPT}")

if [ -z $(docker ps | grep "bistro-competition") -n ]; then
    docker rm beam-competition >> /dev/null
fi

docker run -it --memory="${MEMORY}" --cpus="${CPUS}" --name=bistro-competition -v "${INPUT}":/submission-inputs:ro -v $PWD/output:/output:rw -e "${JJ}" beammodel/beam-competition:0.0.3-SNAPSHOT --scenario "${SCENARIO}" --sample-size "${SIZE}" --iters "${ITERS}"
