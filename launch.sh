#!/bin/bash

cd /home/mde-admin/OceENS

echo "Syncing .venv with uv.lock"
uv sync --frozen

if [ $(ps -aux | grep "oceens.main" | wc -l) -gt 1 ]; then
	echo "Website already launched"
else

	echo "Launching Website with screen"
	screen -d -m bash -c "source .venv/bin/activate && python -u -m oceens.main 2> >(tee -a app.error) | tee -a app.log"
fi

if [ $(ps -aux | grep "oceens-summaries" | wc -l) -gt 1 ]; then
	echo "Summaries generator already launched"
else

	echo "Launching Summaries generator with screen"
	screen -d -m bash -c "source .venv/bin/activate && PYTHONUNBUFFERED=1 oceens-summaries 2> >(tee -a summaries.error) | tee -a summaries.log"
fi




