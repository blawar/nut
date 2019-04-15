#!/usr/bin/env bash
echo "Starting mult-arch build on docker. manifest commands require experimental docker daemon AND experimental docker-cli."
set -e
IMAGE=doctorpangloss/nut
# TODO: This should probably be updated automatically elsewhere or by a different way
META_TAG=1.3

# Only download the qemu-arm-static images if we're on linux. This is most relevant for building on travis automatically
if [[ "$OSTYPE" == "linux-gnu" ]] ; then
  curl https://lsio-ci.ams3.digitaloceanspaces.com/qemu-arm-static -o qemu-arm-static
  curl https://lsio-ci.ams3.digitaloceanspaces.com/qemu-aarch64-static -o qemu-aarch64-static
  chmod +x qemu-*
fi

docker build -f Dockerfile -t "${IMAGE}:amd64-${META_TAG}" .
docker build -f Dockerfile.aarch64 -t "${IMAGE}:arm32v7-${META_TAG}" .
docker build -f Dockerfile.armhf -t "${IMAGE}:arm64v8-${META_TAG}" .

docker tag "${IMAGE}:amd64-${META_TAG}" "${IMAGE}:amd64-latest"
docker tag "${IMAGE}:arm32v7-${META_TAG}" "${IMAGE}:arm32v7-latest"
docker tag "${IMAGE}:arm64v8-${META_TAG}" "${IMAGE}:arm64v8-latest"
docker push "${IMAGE}:amd64-${META_TAG}"
docker push "${IMAGE}:arm32v7-${META_TAG}"
docker push "${IMAGE}:arm64v8-${META_TAG}"
docker push "${IMAGE}:amd64-latest"
docker push "${IMAGE}:arm32v7-latest"
docker push "${IMAGE}:arm64v8-latest"
docker manifest push --purge "${IMAGE}:latest" || :
docker manifest create "${IMAGE}:latest" "${IMAGE}:amd64-latest" "${IMAGE}:arm32v7-latest" "${IMAGE}:arm64v8-latest"
docker manifest annotate "${IMAGE}:latest" "${IMAGE}:arm32v7-latest" --os linux --arch arm
docker manifest annotate "${IMAGE}:latest" "${IMAGE}:arm64v8-latest" --os linux --arch arm64 --variant v8
docker manifest push --purge "${IMAGE}:${META_TAG}" || :
docker manifest create "${IMAGE}:${META_TAG}" "${IMAGE}:amd64-${META_TAG}" "${IMAGE}:arm32v7-${META_TAG}" "${IMAGE}:arm64v8-${META_TAG}"
docker manifest annotate "${IMAGE}:${META_TAG}" "${IMAGE}:arm32v7-${META_TAG}" --os linux --arch arm
docker manifest annotate "${IMAGE}:${META_TAG}" "${IMAGE}:arm64v8-${META_TAG}" --os linux --arch arm64 --variant v8
docker manifest push --purge "${IMAGE}:latest"
docker manifest push --purge "${IMAGE}:${META_TAG}"