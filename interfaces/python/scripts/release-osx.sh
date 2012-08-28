#!/bin/sh
# Creates the OS X installer package and puts it in a disk image

FATLIB=../../fatbuild/libigraph.dylib
PYTHON_VERSIONS="2.5 2.6 2.7"

# Check whether we are running the script on Mac OS X
which hdiutil >/dev/null || ( echo "This script must be run on OS X"; exit 1 )

# Find the directory with setup.py
CWD=`pwd`
while [ ! -f setup.py ]; do cd ..; done

# Extract the version number from setup.py
VERSION=`cat setup.py | grep "version =" | cut -d '=' -f 2 | tr -d "', "`

# Ensure that the igraph library we are linking to is a fat binary
if [ ! -f ${FATLIB} ]; then
  pushd ../.. && tools/fatbuild.sh && popd
  if [ ! -f ${FATLIB} ]; then
    echo "Failed to build fat igraph library: ${FATLIB}"
    exit 1
  fi
fi
if [ `file ${FATLIB} | grep -c "binary with 2 architectures"` -lt 1 ]; then
  echo "${FATLIB} is not a universal binary"
  exit 2
fi

# Clean up the previous build directory
rm -rf build/

# Set up ARCHFLAGS to ensure that we build a multi-arch Python extension
export ARCHFLAGS="-arch i386 -arch x86_64"

# For each Python version, build the .mpkg and the .dmg
for PYVER in $PYTHON_VERSIONS; do
  python$PYVER setup.py build_ext -I ../../include -L `dirname $FATLIB` || exit 3
  python$PYVER setup.py bdist_mpkg || exit 4
  MPKG="dist/python_igraph-${VERSION}-py${PYVER}-macosx10.5.mpkg"
  if [ ! -f $MPKG ]; then
    MPKG="dist/python_igraph-${VERSION}-py${PYVER}-macosx10.6.mpkg"
    if [ ! -f $MPKG ]; then
      MPKG="dist/python_igraph-${VERSION}-py${PYVER}-macosx10.7.mpkg"
    fi
  fi
  DMG=dist/`basename $MPKG .mpkg`.dmg
  rm -f ${DMG}
  hdiutil create -volname "python-igraph ${VERSION}" -layout NONE -srcfolder $MPKG $DMG
  rm -rf ${MPKG}
done

cd $CWD