.PHONY: vagrant test

test:
	echo args = "$(ARGS)"

vagrant:
	   ansible-playbook -i ./inventory/vagrant.ini $(ARGS) ./playbook.yml
