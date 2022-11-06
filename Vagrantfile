# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  # For a complete reference, please see the online documentation at
  # https://docs.vagrantup.com.

  # Every Vagrant development environment requires a box. You can search for
  # boxes at https://vagrantcloud.com/search.
  config.vm.box = "ubuntu/focal64"
  config.vm.box_check_update = false
  config.vm.network "private_network", type: "dhcp" #, virtualbox__intnet: true
  # config.vm.network "forwarded_port", guest: 80, host: 8080
  config.ssh.insert_key = false

  config.vm.define "master" do |master|
    master.vm.box = "ubuntu/focal64"
  end

  config.vm.provider "virtualbox" do |vb|
    vb.memory = "2048"
    vb.cpus = "2"
  end

  # config.vm.provision "shell", inline: <<-SHELL
  #   apt-get update
  #   apt-get install -y apache2
  # SHELL
end
