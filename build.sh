#!/bin/bash
# Script to build production config bundles for MPF. Includes the production.yaml
# config file for embedded machines (production builds don't accept command-line
# config arguments)
echo "Building production bundle for Mass Effect 2 Pinball..."
python -m mpf build production_bundle -c config,production

# When running in a pipx environment, use the following:
# /Users/anthony/.local/pipx/venvs/mpf/bin/python3 -m mpf build production_bundle -c config,production
