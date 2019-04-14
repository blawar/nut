FROM lsiobase/alpine:3.9

# TODO: We're including the entire LSIO python command since we still need the build-dependencies packages to compile hactool if it ever gets used again. Also, this way we use the multi-arch docker images that Linux Server makes, but with python3.

RUN \
 echo "**** install build packages ****" && \
 apk add --no-cache --virtual=build-dependencies \
	autoconf \
	automake \
	freetype-dev \
	g++ \
	gcc \
	jpeg-dev \
	lcms2-dev \
	libffi-dev \
	libpng-dev \
	libwebp-dev \
	linux-headers \
	make \
	openjpeg-dev \
	openssl-dev \
	python3-dev \
	tiff-dev \
	zlib-dev && \
 echo "**** install runtime packages ****" && \
 apk add --no-cache \
	curl \
	freetype \
	git \
	lcms2 \
	libjpeg-turbo \
	libwebp \
	openjpeg \
	openssl \
	p7zip \
	py3-lxml \
	python3 \
	tar \
	tiff \
	unrar \
	unzip \
	vnstat \
	wget \
	xz \
	zlib && \
 echo "**** use ensure to check for pip and link /usr/bin/pip3 to /usr/bin/pip ****" && \
 python3 -m ensurepip && \
 rm -r /usr/lib/python*/ensurepip && \
 if \
	[ ! -e /usr/bin/pip ]; then \
	ln -s /usr/bin/pip3 /usr/bin/pip ; fi && \
 echo "**** install pip packages ****" && \
 pip install --no-cache-dir -U \
	pip \
	setuptools && \
 pip install -U \
	configparser \
	ndg-httpsclient \
	notify \
	paramiko \
	pillow \
	psutil \
	pyopenssl \
	requests \
	setuptools \
	urllib3 \
	virtualenv && \
 echo "**** clean up ****" && \
 apk del --purge \
	build-dependencies && \
 rm -rf \
	/root/.cache \
	/tmp/*

# TODO: For now, we aren't going to compile hactool, since it doesn't appear to be used anywhere

# Install the dependencies
RUN pip install -U colorama pyopenssl requests tqdm unidecode image bs4 urllib3 flask

ENV PYTHONIOENCODING="UTF-8"

# Install the nut application from the root of this repo
# TODO: Install from git directly so that the image stays up to date. Not sure if we can ever do that though.
ADD . /app/nut

# Copy s6 overlay files
COPY root/ /

EXPOSE 9000
VOLUME config/ games/ data/

ENV NUT_CONFIG_PATH=/config
ENV NUT_SCAN_PATH=/games
ENV NUT_SCAN_DEBOUNCE_SECONDS=30.0