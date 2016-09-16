#!/bin/bash

ROOTFSURL="http://opensource.nextthing.co/chippian/mlc-nand-testing-rootfs/server-rootfs.tar.gz"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OUTPUT_DIR=$1

if [ ! $OUTPUT_DIR ]; then
	OUTPUT_DIR=$DIR
fi

cd $OUTPUT_DIR

# Build uboot
if [ ! -d CHIP-u-boot ]; then
	echo "No U-Boot repo found, cloning repo..."
	git clone https://github.com/NextThingCo/CHIP-u-boot.git
	cd CHIP-u-boot
	git checkout -b nextthing/2016.01/next-mlc origin/nextthing/2016.01/next-mlc
	cd ..
fi

echo "Building U-Boot..."
cd CHIP-u-boot
git pull
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- CHIP_defconfig
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)
cd ..

# Build Linux
if [ ! -d CHIP-linux ]; then
	echo "No kernel repo found, cloning repo..."
	git clone https://github.com/NextThingCo/CHIP-linux.git
	cd CHIP-linux
	git checkout -b nextthing/4.4/next-mlc origin/nextthing/4.4/next-mlc
	touch .scmversion
	cd ..
	echo "Copying .config..."
	cp $DIR/config-4.4.13-ntc-nand-testing CHIP-linux/.config
fi

echo "Building kernel..."
cd CHIP-linux
git pull
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)
cd ..

# Build MTD utils
if [ ! -d CHIP-mtd-utils ]; then
	echo "No mtd-utils found, cloning repo..."
	git clone https://github.com/NextThingCo/CHIP-mtd-utils.git
	cd CHIP-mtd-utils
	git checkout -b nextthing/1.5.2/next-mlc origin/nextthing/1.5.2/next-mlc
	cd ..
fi

echo "Building mtd-utils..."
cd CHIP-mtd-utils
git pull
make ARCH=arm CROSS_COMPILE=arm-linux-gnueabi- -j$(nproc)
cd ..

# Download rootfs
echo "Downloading rootfs..."
curl -o rootfs.tar $ROOTFSURL

echo "Creating images..."
rm -rf images
mkdir -p images
fakeroot tar -xf rootfs.tar -C images/

cp CHIP-linux/arch/arm/boot/dts/sun5i-r8-chip.dts images/rootfs/boot/
cp CHIP-linux/arch/arm/boot/zImage images/rootfs/boot/

git clone https://chipnandtester:chippydoesntlikecheapandshitty@github.com/NextThingCo/CHIP-nandTests.git images/rootfs/root/CHIP-nandTests
cp images/rootfs/root/CHIP-nandTests/bootstrap.service images/rootfs/etc/systemd/system/
mkdir -p images/rootfs/etc/systemd/system/network-online.target.wants
ln -s /etc/systemd/system/bootstrap.service images/rootfs/etc/systemd/system/network-online.target.wants/bootstrap.service

cp $DIR/wpa_supplicant.service images/rootfs//lib/systemd/system/
cp $DIR/system.conf images/rootfs/etc/systemd/

fakeroot CHIP-mtd-utils/mkfs.ubifs/mkfs.ubifs -d images/rootfs -m 16384 -e 0x1F8000 -c 4096 -o images/rootfs.ubifs
CHIP-mtd-utils/ubi-utils/ubinize -o images/chip.ubi -p 0x400000 -m 0x4000 -M dist3 $DIR/ubinize.cfg

dd if=CHIP-u-boot/u-boot-dtb.bin of=images/uboot.bin bs=4M conv=sync

img2simg images/chip.ubi images/chip.ubi.sparse $((4 * 1024 * 1024))
