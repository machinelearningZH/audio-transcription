# Copyright (c) 2024 Gerichte Kanton Aargau

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated 
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to 
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to 
# whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the 
# Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR 
# PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE 
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
# DEALINGS IN THE SOFTWARE.

FROM python:3.10

ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/lib/x86_64-linux-gnu/

WORKDIR /usr/src/app
COPY . .

RUN apt-get update
RUN apt-get install ffmpeg wget -y

RUN wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb
RUN dpkg -i cuda-keyring_1.1-1_all.deb

RUN apt-get update

RUN apt-get -y install cudnn9-cuda-12

RUN pip3 install torch torchvision torchaudio
RUN pip3 install -r requirements.txt
RUN pip3 uninstall onnxruntime --yes
RUN pip3 install --force-reinstall onnxruntime-gpu
RUN pip3 install --force-reinstall -v "numpy==1.26.3"

RUN pip3 install ffprobe
RUN pip3 install hapless

CMD [ "bash", "./bootup.sh" ]