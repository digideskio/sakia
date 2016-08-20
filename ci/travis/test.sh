#!/usr/bin/env bash

eval "$(pyenv init -)"

cd $HOME/build/duniter/sakia
pyenv shell $PYENV_PYTHON_VERSION
if [ $TRAVIS_OS_NAME == "linux" ]
then
    export DISPLAY=:0
    coverage run --source=sakia.core,sakia.gui,sakia.models setup.py test
else
    python setup.py test
fi


