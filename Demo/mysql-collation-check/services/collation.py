from config import TARGET_CHARSET, TARGET_COLLATION


def column_needs_fix(column):
    collation = column['COLLATION_NAME']
    charset = column['CHARACTER_SET_NAME']
    return collation is not None and (
        collation != TARGET_COLLATION or charset != TARGET_CHARSET
    )


def annotate_table(table, column_issues):
    collation = table['TABLE_COLLATION'] or ''
    charset = collation.split('_')[0] if collation else ''
    issues = column_issues.get(table['TABLE_NAME'], [])

    table['TABLE_CHARSET'] = charset
    table['charset_mismatch'] = charset != TARGET_CHARSET
    table['table_need_fix'] = (
        table['charset_mismatch'] or collation != TARGET_COLLATION
    )
    table['COLUMN_ISSUES'] = issues
    table['COLUMN_ISSUE_COUNT'] = len(issues)
    table['need_fix'] = table['table_need_fix'] or bool(issues)
    return table


def fetch_column_issues(cursor, database):
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, COLUMN_TYPE,
               CHARACTER_SET_NAME, COLLATION_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND COLLATION_NAME IS NOT NULL
          AND (COLLATION_NAME != %s OR CHARACTER_SET_NAME != %s)
        ORDER BY TABLE_NAME, ORDINAL_POSITION
    """, (database, TARGET_COLLATION, TARGET_CHARSET))

    issues = {}
    for row in cursor.fetchall():
        issues.setdefault(row['TABLE_NAME'], []).append({
            'name': row['COLUMN_NAME'],
            'type': row['COLUMN_TYPE'],
            'charset': row['CHARACTER_SET_NAME'] or '-',
            'collation': row['COLLATION_NAME'] or '-'
        })
    return issues


def build_column_definition(column):
    parts = [column['COLUMN_TYPE']]
    if column['CHARACTER_SET_NAME'] is not None:
        parts.append(f'CHARACTER SET {TARGET_CHARSET} COLLATE {TARGET_COLLATION}')

    parts.append('NULL' if column['IS_NULLABLE'] == 'YES' else 'NOT NULL')

    default = column.get('COLUMN_DEFAULT')
    if default is not None:
        if default == 'CURRENT_TIMESTAMP':
            parts.append('DEFAULT CURRENT_TIMESTAMP')
        elif (column['COLUMN_TYPE'] in ('timestamp', 'datetime')
              and 'on update' in (column.get('EXTRA') or '').lower()):
            parts.append(f'DEFAULT {default}')
        else:
            parts.append(f"DEFAULT '{default}'")

    extra = column.get('EXTRA') or ''
    if extra:
        parts.append(extra)

    comment = column.get('COLUMN_COMMENT') or ''
    if comment:
        parts.append(f"COMMENT '{comment}'")

    return ' '.join(parts)
