#!/bin/bash

sudo apt-get update
sudo apt-get -y install iperf3 git zsh curl vim tmux python-pip xorg-dev libx11-dev htop git make g++ gcc emacs

# Mellanox OFED
# http://www.mellanox.com/related-docs/prod_software/Mellanox_OFED_Linux_User_Manual_v4.0.pdf
wget http://www.mellanox.com/downloads/ofed/MLNX_OFED-4.0-2.0.0.1/MLNX_OFED_LINUX-4.0-2.0.0.1-ubuntu16.04-x86_64.tgz
tar xfz ./MLNX_OFED_LINUX-4.0-2.0.0.1-ubuntu16.04-x86_64.tgz
sudo ./MLNX_OFED_LINUX-4.0-2.0.0.1-ubuntu16.04-x86_64/mlnxofedinstall --force --dpdk
sudo /etc/init.d/openibd restart

# Mellanox DPDK
# http://www.mellanox.com/related-docs/prod_software/MLNX_DPDK_Quick_Start_Guide_v16.11_2.3.pdf
wget http://www.mellanox.com/downloads/Drivers/MLNX_DPDK_16.11_2.3.tar.gz
tar xfz ./MLNX_DPDK_16.11_2.3.tar.gz
sudo connectx_port_config -c eth,eth
sudo sh -c "echo 'options mlx4_core log_num_mgm_entry_size=-7' >> /etc/modprobe.d/mlx4.conf"
sudo /etc/init.d/openibd restart 
cd ./MLNX_DPDK_16.11_2.3
make install T=x86_64-native-linuxapp-gcc
cd ../

# Huge pages
# http://dpdk.org/doc/guides-16.04/linux_gsg/sys_reqs.html
sudo sed -i -r 's/GRUB_CMDLINE_LINUX=\"(.*)\"/GRUB_CMDLINE_LINUX=\"\1 default_hugepagesz=1G hugepagesz=1G hugepages=4\"/' /etc/default/grub
sudo update-grub
sudo mkdir /mnt/huge_1GB
sudo sh -c "echo 'nodev /mnt/huge_1GB hugetlbfs pagesize=1GB 0 0' >> /etc/fstab"

printf "\n%s\n%s\n" 'export RTE_SDK=/users/mukerjee/MLNX_DPDK_16.11_2.3' 'export RTE_TARGET=x86_64-native-linuxapp-gcc' >> /users/mukerjee/.bashrc
sudo reboot