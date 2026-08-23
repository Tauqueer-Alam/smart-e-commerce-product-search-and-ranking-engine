#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Compiling C++ DSA Engine for Linux..."
cd dsa_engine
g++ -shared -o libengine.so -fPIC engine.cpp -O2 -std=c++17
cd ..

echo "Build complete."
