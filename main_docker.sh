#!/bin/bash

set -e

BUILD_RUN="docker build -f Dockerfile.run -t sardina ."
BUILD_CRON="docker build -f Dockerfile.cron -t sardina-cron ."
RUN="docker run --rm -v $PWD/output:/root/sardina/output -it sardina"
CRON="docker run --rm -itd sardina-cron"

rebuild_sardina_image_if_does_not_exist() {
  if [[ -z  $(docker image ls | grep "sardina ") ]]; then
    echo "sardina Docker image not found. Rebuilding..."
    echo ""
    $BUILD_RUN
  fi
}

rebuild_sardina_cron_image_if_does_not_exist() {
  if [[ -z  $(docker image ls | grep "sardina-cron ") ]]; then
    echo "sardina-cron Docker image not found. Rebuilding..."
    echo ""
    $BUILD_CRON
  fi
}

run_sardina_docker() {
  rebuild_sardina_image_if_does_not_exist
  if [ ! -d output ]; then
    mkdir output
  fi
  $RUN
  echo "See output files in output directory/<timestamp>"
  exit 0
}

run_sardina_cron_docker() {
  rebuild_sardina_cron_image_if_does_not_exist
  $CRON
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
