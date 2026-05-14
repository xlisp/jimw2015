#!/bin/bash
pyini () {
	__conda_setup="$('/opt/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
	if [ $? -eq 0 ]
	then
		eval "$__conda_setup"
	else
		if [ -f "/opt/anaconda3/etc/profile.d/conda.sh" ]
		then
			. "/opt/anaconda3/etc/profile.d/conda.sh"
		else
			export PATH="/opt/anaconda3/bin:$PATH"
		fi
	fi
	unset __conda_setup
}
pyini
export https_proxy=http://127.0.0.1:6789 http_proxy=http://127.0.0.1:6789 all_proxy=socks5://127.0.0.1:6789
conda activate torch
cd ~/PyPro/jimw2015 && python app.py
