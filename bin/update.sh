#!/usr/bin/env bash

echo "Updating BeamCompetitions, building image, and pushing to Docker Hub"

git pull && gdpi

echo "Done!"
