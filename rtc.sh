.\repo.bat launch source/apps/my_company.my_editor.kit \
    --enable omni.services.streamclient.webrtc \
    --/exts/omni.services.streamclient.webrtc/ice_servers/1/urls/0="turn:52.14.61.122:3478?transport=udp" \
    --/exts/omni.services.streamclient.webrtc/ice_servers/1/urls/1="turn:52.14.61.122:3478?transport=tcp" \
    --/exts/omni.services.streamclient.webrtc/ice_servers/1/username="admin" \
    --/exts/omni.services.streamclient.webrtc/ice_servers/1/credential="qwerty" \
    --no-window \
    --allow-root