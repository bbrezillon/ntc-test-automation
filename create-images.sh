#!/bin/bash

ROOTFSURL="http://opensource.nextthing.co/chippian/mlc-nand-testing-rootfs/server-rootfs.tar.gz"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Build uboot
if [ ! -d CHIP-u-boot ]; then
	git clone https://github.com/NextThingCo/CHIP-u-boot.git
	cd CHIP-u-boot
	git checkout -b nextthing/2016.01/next-mlc origin/nextthing/2016.01/next-mlc
	cd ..
fi

cd CHIP-u-boot
git pull
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- CHIP_defconfig
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)
cd ..

# Build Linux
if [ ! -d CHIP-linux ]; then
	git clone https://github.com/NextThingCo/CHIP-linux.git
	cd CHIP-linux
	git checkout -b nextthing/4.4/next-mlc origin/nextthing/4.4/next-mlc
	touch .scmversion
	cd ..
	cp $DIR/config-4.4.13-ntc-nand-testing CHIP-linux/.config
fi

cd CHIP-linux
git pull
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)
cd ..

# Build MTD utils
if [ ! -d CHIP-mtd-utils ]; then
	git clone https://github.com/NextThingCo/CHIP-mtd-utils.git
	cd CHIP-mtd-utils
	git checkout -b nextthing/1.5.2/next-mlc origin/nextthing/1.5.2/next-mlc
	cd ..
fi

cd CHIP-mtd-utils
git pull
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)
cd ..

# Download rootfs
curl -o rootfs.tar $ROOTFSURL

rm -rf images
mkdir -p images
fakeroot tar -xf rootfs.tar -C images/

cp CHIP-linux/arch/arm/boot/dts/sun5i-r8-chip.dts images/rootfs/boot/
cp CHIP-linux/arch/arm/boot/zImage images/rootfs/boot/

CHIP-mtd-utils/mkfs.ubifs/mkfs.ubifs -d images/rootfs -m 16384 -e 0x1F8000 -c 4096 -o images/rootfs.ubifs
CHIP-mtd-utils/ubi-utils/ubinize -o images/chip.ubi -p 0x400000 -m 0x4000 -M dist3 $DIR/ubinize.cfg

dd if=CHIP-u-boot/u-boot-dtb.bin of=images/uboot.bin bs=4M conv=sync

img2simg images/chip.ubi images/chip.ubi.sparse $((4 * 1024 * 1024))