#!/bin/bash

source ./.env

uvicorn src.main:app --reload --host 0.0.0.0 --port $PORT