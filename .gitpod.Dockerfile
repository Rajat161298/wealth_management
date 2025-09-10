FROM gitpod/workspace-full:latest

# Install Flutter
ENV FLUTTER_HOME=/home/gitpod/flutter
RUN git clone https://github.com/flutter/flutter.git -b stable $FLUTTER_HOME --depth=1 \
    && echo 'export PATH="$FLUTTER_HOME/bin:$PATH"' >> /home/gitpod/.bashrc

RUN python3 -m pip install --upgrade pip

EXPOSE 8080 8000
