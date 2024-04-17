#!/bin/sh

base_image="ghcr.io/nothing4you/activitypub-federation-queue-batcher/base:local"

docker buildx build -t "$base_image" .

for app in inbox-receiver batch-sender batch-receiver
do
  docker buildx build \
    -f "$app.Dockerfile" \
    -t "ghcr.io/nothing4you/activitypub-federation-queue-batcher/$app:local" \
    --build-arg "BASE_IMAGE=$base_image" .
done
