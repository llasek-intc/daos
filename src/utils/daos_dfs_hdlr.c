/**
 * (C) Copyright 2016-2021 Intel Corporation.
 *
 * SPDX-License-Identifier: BSD-2-Clause-Patent
 */

/*
 * daos_dfs_hdlr.c - handler function for dfs ops (set/get chunk size, etc.)
 * invoked by daos(8) utility
 */

#define D_LOGFAC	DD_FAC(client)

#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <daos.h>
#include <daos/common.h>
#include <daos/debug.h>

#include "daos_types.h"
#include "daos_fs.h"
#include "daos_uns.h"
#include "daos_hdlr.h"

int
fs_dfs_hdlr(struct cmd_args_s *ap)
{
	int		rc, rc2;
	int		flags;
	dfs_t		*dfs;

	rc = daos_pool_connect(ap->p_uuid, ap->sysname, DAOS_PC_RW,
			       &ap->pool, NULL, NULL);
	if (rc != 0) {
		fprintf(stderr,
			"failed to connect to pool "DF_UUIDF": %s (%d)\n",
			DP_UUID(ap->p_uuid), d_errdesc(rc), rc);
		return rc;
	}

	rc = daos_cont_open(ap->pool, ap->c_uuid, DAOS_COO_RW | DAOS_COO_FORCE,
			    &ap->cont, NULL, NULL);
	if (rc != 0) {
		fprintf(stderr,
			"failed to open container "DF_UUIDF ": %s (%d)\n",
			DP_UUID(ap->c_uuid), d_errdesc(rc), rc);
		D_GOTO(out_disconnect, rc);
	}

	if (ap->fs_op == FS_SET_OCLASS || ap->fs_op == FS_SET_CSIZE)
		flags = O_RDWR;
	else
		flags = O_RDONLY;

	rc = dfs_mount(ap->pool, ap->cont, flags, &dfs);
	if (rc) {
		fprintf(stderr,
			"failed to mount container "DF_UUIDF": %s (%d)\n",
			DP_UUID(ap->c_uuid), strerror(rc), rc);
		D_GOTO(out_close, rc = daos_errno2der(rc));
	}

	if (ap->dfs_prefix) {
		rc = dfs_set_prefix(dfs, ap->dfs_prefix);
		if (rc)
			D_GOTO(out_umount, rc);
	}

	switch (ap->fs_op) {
	case FS_GET_OCLASS:
	case FS_GET_CSIZE:
	{
		dfs_obj_info_t	info;
		dfs_obj_t	*obj;
		char		name[16];

		rc = dfs_lookup(dfs, ap->dfs_path, flags, &obj, NULL, NULL);
		if (rc) {
			fprintf(stderr, "failed to lookup %s (%s)\n",
				ap->dfs_path, strerror(rc));
			D_GOTO(out_umount, rc);
		}
		rc = dfs_obj_get_info(obj, &info);
		if (rc) {
			fprintf(stderr, "failed to get obj info (%s)\n",
				strerror(rc));
			dfs_release(obj);
			D_GOTO(out_umount, rc);
		}

		rc = dfs_release(obj);
		if (rc) {
			fprintf(stderr, "failed to release obj handle (%s)\n",
				strerror(rc));
			D_GOTO(out_umount, rc);
		}

		daos_oclass_id2name(info.doi_oclass_id, name);
		printf("Object Class = %s (%u)\n", name, info.doi_oclass_id);
		printf("Object Chunk Size = %zu\n", info.doi_chunk_size);
		break;
	}
	case FS_SET_OCLASS:
		printf("FS_SET_OCLASS");
		break;
	case FS_SET_CSIZE:
		printf("FS_SET_CSIZE");
		break;
	default:
		D_ASSERT(0);
	}

out_umount:
	rc2 = dfs_umount(dfs);
	if (rc2 != 0)
		fprintf(stderr, "failed to umount DFS container\n");
	if (rc == 0)
		rc = rc2;
out_close:
	rc2 = daos_cont_close(ap->cont, NULL);
	if (rc2 != 0)
		fprintf(stderr,
			"failed to close container "DF_UUIDF ": %s (%d)\n",
			DP_UUID(ap->c_uuid), d_errdesc(rc2), rc2);
	if (rc == 0)
		rc = rc2;
out_disconnect:
	rc2 = daos_pool_disconnect(ap->pool, NULL);
	if (rc2 != 0)
		fprintf(stderr,
			"failed to disconnect from pool "DF_UUIDF": %s (%d)\n",
			DP_UUID(ap->p_uuid), d_errdesc(rc2), rc2);
	if (rc == 0)
		rc = rc2;

	return rc;
}
