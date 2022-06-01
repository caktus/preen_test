# Backup Verification

## Storage and access
In the event a restore from a historical backup is needed, access to the [Caktus AssumeRole is required](https://github.com/caktus/caktus-hosting-services/blob/main/docs/aws-assumerole.md#aws-accounts).
Once you have that access, you can use invoke tools to pull historical backups.

Documentation for the invoke tasks can be found [here](https://github.com/caktus/invoke-kubesae).

A quick test to make sure you have access is to run the following command:

```shell
    (preen_test)$ inv utils.get-db-backup --list
```

If you get a list, you have access.


### Database Restore From Hosting

The following will pull the latest backup for the project

```shell
    (preen_test)$ inv utils.get-db-backup
```

This will pull the most recent monthly backup.

```shell
    (preen_test)$ inv utils.get-db-backup --latest=monthly
```

You should now have a file similar to ``daily-preen_test-202103030000.pgdump`` in your project root.

You can find more usage examples and documentation on this invoke task [here](https://github.com/caktus/invoke-kubesae/blob/72cca9f1921f83574e58804d2d57f6da93019ef0/kubesae/utils.py#L19).



**Restore the file Locally**

```sh
    (preen_test)$ pg_restore --no-owner --clean --if-exists --dbname preen_test < daily-preen_test-202103030000.pgdump
```


### Restore staging from production

First restore the database on staging to the dump from backup.

```shell
    (preen_test)$ inv staging pod.restore-db-from-dump --db-var="DATABASE_URL" --filename=".\daily-preen_test-202103030000.pgdump"
```

**Fix the Wagtail Site**
At this point the database is installed, but its site is configured for ``www.preen_test.com``.
Login to wagtail admin and change it to staging:

Create a superuser account if needed:

```shell
    (preen_test)$ inv staging pod
    appuser@app-abc123f4-349sh:/code$ ./manage.py createsuperuser
```

Login to ``https://staging.preen_test.org/`` and navigate to `Settings->Sites`, and change the
Hostname to `staging.preen_test.org`. You can now visit https://staging.preen_test.org/ without error. 

It is possible that you will see broken images. If so you should reset the media from production.

**Restore staging media from production**

Run the sync-media command with a ``--dry-run`` parameter to gut check the process.

```sh
    (preen_test)$  inv production aws.sync-media --dry-run
```

If everything looks good, run it without the ``--dry-run`` parameter.

Reload https://staging.preen_test.org/ the site should mirror production with no broken assets. 
