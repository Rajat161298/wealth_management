FROM gitpod/workspace-full:latest

# Install Python pip upgrades and other essentials (if needed)
RUN python3 -m pip install --upgrade pip setuptools wheel || true

# Install Flutter (stable) into $HOME/flutter
ENV FLUTTER_HOME=/home/gitpod/flutter
ENV PATH="$FLUTTER_HOME/bin:$PATH"

RUN git clone https://github.com/flutter/flutter.git -b stable $FLUTTER_HOME --depth=1 \
    && chmod -R a+rx $FLUTTER_HOME

# Optionally run flutter precache on image build (commented because it can be heavy)
# RUN $FLUTTER_HOME/bin/flutter doctor -v || true

# Expose default ports used by the tasks
EXPOSE 8000 8080
