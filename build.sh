#!/bin/bash
# Script to build production config bundles for MPF. Includes the production.yaml
# config file for embedded machines (production builds don't accept command-line
# config arguments)
mpf build production_bundle -c config,production
