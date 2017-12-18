.PHONY: vagrant test

test:
	echo args = "$(ARGS)"

vagrant:
	   ansible-playbook -b -i ./inventory/vagrant.ini $(ARGS) ./playbook.yml
