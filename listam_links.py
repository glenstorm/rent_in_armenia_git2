"""Normalize list.am item URLs so query variants map to one listing."""


def normalize_listam_link(href):
    """
    Canonicalize a list.am item URL.

    Strips query/fragment (e.g. ?ld_src=2) and makes relative /ru/item/... absolute.
    """
    if not href:
        return None
    link = str(href).strip()
    if not link:
        return None
    if link.startswith("/"):
        link = "https://www.list.am" + link
    link = link.split("#", 1)[0].split("?", 1)[0]
    return link or None


def find_listing_id_by_link(cursor, table, link):
    """
    Find a row id by canonical link, including legacy rows that still have ?query.
    """
    canonical = normalize_listam_link(link)
    if not canonical:
        return None

    cursor.execute(
        f"SELECT id FROM {table} WHERE link = ? LIMIT 1",
        (canonical,),
    )
    row = cursor.fetchone()
    if row:
        return row[0]

    cursor.execute(
        f"SELECT id FROM {table} WHERE link LIKE ? LIMIT 1",
        (canonical + "?%",),
    )
    row = cursor.fetchone()
    if row:
        return row[0]
    return None


def dedupe_table_by_link(connection, table, history_table, listing_fk="listing_id"):
    """
    Merge rows that share the same canonical item URL.

    Keeps the lowest id, reassigns history rows, deletes duplicates, and
    rewrites the survivor link to the canonical form.
    Returns the number of duplicate rows removed.
    """
    cur = connection.cursor()
    rows = cur.execute(f"SELECT id, link FROM {table}").fetchall()
    groups = {}
    for listing_id, link in rows:
        key = normalize_listam_link(link)
        if not key:
            continue
        groups.setdefault(key, []).append(listing_id)

    removed = 0
    for canonical, ids in groups.items():
        ids = sorted(set(ids))
        keep_id = ids[0]
        drop_ids = ids[1:]

        for drop_id in drop_ids:
            cur.execute(
                f"UPDATE {history_table} SET {listing_fk} = ? WHERE {listing_fk} = ?",
                (keep_id, drop_id),
            )
            cur.execute(f"DELETE FROM {table} WHERE id = ?", (drop_id,))
            removed += 1

        cur.execute(
            f"UPDATE {table} SET link = ? WHERE id = ?",
            (canonical, keep_id),
        )

    connection.commit()
    return removed
