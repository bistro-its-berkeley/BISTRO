#RUN apt-get update \
#    && apt-get -y install openjdk-8-jdk \
#    && rm -rf /var/lib/apt/lists/*
#
#
#ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64
#ENV PATH $JAVA_HOME/bin:$PATH

FROM java:8-jdk
RUN mkdir -p /java8_lol
WORKDIR /java8_lol

FROM python:3.6

RUN mkdir -p /provisioning
WORKDIR /provisioning
RUN mkdir -p /java8_ll
COPY --from=0 /java8_lol /java8_ll
RUN mkdir -p /usr/lib/jvm/java-8-openjdk-amd64
COPY --from=0 /usr/lib/jvm/java-8-openjdk-amd64 /usr/lib/jvm/java-8-openjdk-amd64

ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-amd64
ENV PATH $JAVA_HOME/bin:$PATH

RUN apt-get update && \
    apt-get -yq install \
        build-essential \
        gcc \
        libgeos-dev \
        zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

RUN echo "Installing HDF5..." && \
    apt-cache search hdf5

RUN echo "Installing Spatial Index library..." && \
    mkdir -p /provisioning/spatialindex && \
    cd /provisioning/spatialindex && \
    curl -# -O http://download.osgeo.org/libspatialindex/spatialindex-src-1.8.5.tar.gz && \
    tar -xzf spatialindex-src-1.8.5.tar.gz && \
    cd spatialindex-src-1.8.5 && \
    ./configure --prefix=/usr/local && \
    make -j$(python -c 'import multiprocessing; print(multiprocessing.cpu_count())') && \
    make install && \
    ldconfig && \
    rm -rf /provisioning/spatialindex*

RUN echo "Installing GEOS library..." && \
    mkdir -p /provisioning/geos && \
    cd /provisioning/geos && \
    curl -# -O http://download.osgeo.org/geos/geos-3.5.1.tar.bz2 && \
    tar -xjf geos-3.5.1.tar.bz2 && \
    cd geos-3.5.1 && \
    ./configure && \
    make -j$(python -c 'import multiprocessing; print(multiprocessing.cpu_count())') && \
    make install && \
    ldconfig -v && \
    rm -rf /provisioning/geos*

RUN echo "Installing Proj4 library..." && \
    mkdir -p /provisioning/proj4 && \
    cd /provisioning/proj4 && \
    curl -# -O http://download.osgeo.org/proj/proj-4.9.3.tar.gz && \
    tar -xzf proj-4.9.3.tar.gz && \
    cd proj-4.9.3 && \
    ./configure && \
    make -j$(python -c 'import multiprocessing; print(multiprocessing.cpu_count())') && \
    make install && \
    ldconfig -v && \
    rm -rf /provisioning/proj4

RUN pip install --upgrade numpy

RUN echo "Installing Basemap plotting library..." && \
    mkdir -p /provisioning/matplotlib-basemap && \
    cd /provisioning/matplotlib-basemap && \
    curl -# -o basemap-1.0.7rel.tar.gz https://codeload.github.com/matplotlib/basemap/tar.gz/v1.0.7rel && \
    tar -xzf basemap-1.0.7rel.tar.gz && \
    cd basemap-1.0.7rel && \
    python setup.py install && \
    rm -rf /provisioning/matplotlib-basemap

RUN mkdir -p /provisioning/pandana
RUN echo "Installing pandana library..." && \
    cd /provisioning/pandana && \
    pip install pandana

COPY ./requirements.txt /provisioning
RUN pip install -r /provisioning/requirements.txt

RUN mkdir -p /accessibility
RUN echo "Installing accessibility metrics..."
RUN mkdir -p output/tmp-data
COPY . /accessibility
WORKDIR /
