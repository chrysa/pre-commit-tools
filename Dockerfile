#!/usr/bin/env bash

set -heu

[ -f "${WEB_CONF_FILE}" ] && echo "${WEB_CONF_FILE} exist" || (echo "${WEB_CONF_FILE} not exist" ; exit)

if [ ! -f "${BOOTSTRAPED_FUSIONDIRECTORY_WEB_FILE_PATH}" ] ; then
    echo -e "===================== configure FUSIONDIRECTORY WEB FILE (${WEB_CONF_FILE})"
    sed -i "s/%LDAP_ADMIN_PASSWORD%/$(cat ${LDAP_ADMIN_PASSWORD_FILE})/g" ${WEB_CONF_FILE}

    echo $(date +"%F %T") > "${BOOTSTRAPED_FUSIONDIRECTORY_WEB_FILE_PATH}"
fi

unset BOOTSTRAPED_FUSIONDIRECTORY_WEB_FILE_PATH
unset WEB_CONF_FILE
