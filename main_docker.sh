#!/bin/bash

HUB="docker.caste.dev"

BUILD_RUN="docker build -f Dockerfile.run -t sardina ."
BUILD_CRON="docker build -f Dockerfile.cron -t sardina-cron ."
RUN="docker run --rm -v $PWD/output:/sardina/output -it sardina"
CRON="docker run --rm  --name sardina-cron -itd sardina-cron"
RUN_HUB="docker run --rm -v $PWD/output:/sardina/output -it $HUB/sardina"
CRON_HUB="docker run --rm  --name sardina-cron -itd $HUB/sardina-cron"

# try pulling from registry first, then run local image, then build
rebuild_sardina_image_if_does_not_exist() {
  $RUN_HUB
  # if non-zero exit code -> not found on hub
  if [[ $? != 0 ]]; then
    if [[ -z  $(docker image ls | grep "sardina ") ]]; then
      echo "sardina Docker image not found. Rebuilding..."
      echo ""
      $BUILD_RUN
    fi
  else
    # tag so that user can run sardina instead of $HUB/sardina (longer to type)
    docker tag "$HUB"/sardina sardina
  fi
}

rebuild_sardina_cron_image_if_does_not_exist() {
  $CRON_HUB
  if [[ $? != 0 ]]; then
    if [[ -z  $(docker image ls | grep "sardina-cron ") ]]; then
      echo "sardina-cron Docker image not found. Rebuilding..."
      echo ""
      $BUILD_CRON
    fi
  else
    docker tag "$HUB"/sardina-cron sardina-cron
  fi
}

run_sardina_docker() {
  rebuild_sardina_image_if_does_not_exist
  if [[ $? != 0 ]]; then
    if [ ! -d output ]; then
      mkdir output
    fi
    $RUN
  fi
  echo "See output files in output directory/<timestamp>"
  exit 0
}

run_sardina_cron_docker() {
  rebuild_sardina_cron_image_if_does_not_exist
  if [[ $? != 0 ]]; then
    $CRON
  fi
  echo "Cron is running inside the container with the hash above every 5 minutes"
  echo "To stop and remove: docker stop <hash>"
  echo "To see logs: docker logs --follow <hash>"
  exit 0
}

# no arguments -> run
if [ $# -eq 0 ]; then
  run_sardina_docker
fi

# one argument -> either run or cron
if [ $# -eq 1 ]; then
  if [ $1 = "--run" ]; then
    run_sardina_docker
  elif [ $1 = "--cron" ]; then
    run_sardina_cron_docker
  elif [ $1 = "--help" ] || [ $1 = "-h" ]; then
    echo "Usage:"
    echo "$0 [--run] -> run sardina inside docker container"
    echo "$0 --cron -> run sardina every 5 minutes inside docker container in the background"
    echo "In both cases this script:"
    echo "  1) tries pulling from $HUB, if not logged in then"
    echo "  2) builds the docker container locally and runs it"
    echo "To login with user and password, before running this script run:"
    echo "  docker login $HUB"
    exit 0
  else
    echo "Unexpected argument: $1"
    echo "Possible arguments: --run or --cron"
    exit -1
  fi
fi

# more than one argument
if [ $# -gt 1 ]; then
  echo "Too many arguments."
  echo "Use --run or --cron"
  exit -1
fi
