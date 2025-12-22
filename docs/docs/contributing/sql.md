# Modifications to SQL database structure

When you modify the SQL database structure, you need to create an Alembic migration.


If you have modified the API database tables in the [models.py](https://github.com/etalab-ia/OpenGateLLM/blob/main/api/sql/models.py) file, you need to create an Alembic migration with the following command:

```bash
alembic -c api/alembic.ini revision --autogenerate -m "message"
```

Then apply the migration with the following command:

```bash
alembic -c api/alembic.ini upgrade head
```

If you want to revert the last migration (or just test it), you can use the following command:

```bash
alembic -c api/alembic.ini downgrade -1
```