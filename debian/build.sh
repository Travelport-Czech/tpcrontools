#!/usr/bin/env bash

set -e

version="$1"
project="$(basename "$(dirname "$PWD")")"
workspace="${project}_${version}"

if ! [[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]-[0-9]+$ ]]; then
  printf 'Must specify version in format x.y.z-n as parameter!\n\n'
  exit 1
fi

if ! [[ -f 'control' ]]; then
  printf 'File "control" does not exist, I create a new one.\n'
  cat > control <<+++CONTROL+++
Package: helloworld
Version: {version}
Section: base
Priority: optional
Architecture: i386
Depends: libsomethingorrather (>= 1.2.13), anotherDependency (>= 1.2.6)
Maintainer: Your Name <you@email.com>
Description: Hello World
 When you need some sunshine, just run this
 small program!
 
 (the space before each line in the description is important)
+++CONTROL+++
fi

[[ -f postinst ]] || touch postinst
[[ -f preinst ]] || touch preinst
[[ -f prerm ]] || touch prerm

if grep -q -F 'Package: helloworld' control; then
  printf 'Edit the "control" file to match your project!\n\n'
  exit 1
fi

if [[ -f "${workspace}.deb" ]]; then
  printf 'File "%s" already exists - remove this manualy!\n\n' "${workspace}.deb"
  exit 1
fi

if [[ -d "${workspace}" ]]; then
  printf 'Directory "%s" already exists - remove this manualy!\n\n' "${workspace}"
  exit 1
fi

mkdir -p "${workspace}/DEBIAN"

for file in ../*; do
  if [[ -f "$file" && -x "$file" ]]; then
    mkdir -p "${workspace}/usr/bin"
    cp "$file" "${workspace}/usr/bin"
  fi
done

if [[ -d "../${project}" ]]; then
  mkdir -p "${workspace}/usr/lib/python3/dist-packages/${project}"
  cp -r "../${project}" "${workspace}/usr/lib/python3/dist-packages/"
  py3clean "${workspace}/usr/lib/python3/dist-packages/${project}"
fi

size=$(( ($(du -b -s "${workspace}" | cut -f 1) + 1023) / 1024 ))
sed -e "s/{version}/${version}/g;s/{size}/${size}/g" control > "${workspace}/DEBIAN/control"

cp postinst preinst prerm "${workspace}/DEBIAN"
sed -i "s/{project}/${project}/g" "${workspace}/DEBIAN/"{postinst,preinst,prerm}
chmod 755 "${workspace}/DEBIAN/"{postinst,preinst,prerm}

(
  cd "${workspace}"
  find * -type f -print0 | xargs -0 md5sum | grep -E -v '^[0-9a-f]+\s+DEBIAN' > 'DEBIAN/md5sums'
)

fakeroot dpkg-deb --build "${workspace}"

rm -rf "${workspace}"

git add "${workspace}.deb"
git commit -m "Release version ${version}"
