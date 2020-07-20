#!/bin/bash
# Script to build production config bundles for MPF. Includes the production.yaml
# config file for embedded machines (production builds don't accept command-line
# config arguments)
echo "Building production bundle for Mass Effect 2 Pinball..."
mpf build production_bundle -c config,production
