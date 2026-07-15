## Section 4 — Written Architecture Review

### Question A — Django Admin Performance

When I looked at this the first thing I'd check is the count query.
Django admin runs SELECT COUNT(*) on every page load to show total
records. On 500k rows this is slow even with a primary key index because
it's counting everything. The fix is to set show_full_result_count =
False on the ModelAdmin. This stops Django from running the full count
and just shows "show all" instead of the exact number.

Second thing I'd check is list_display. If you have ForeignKey fields
showing in the list like customer name or product name, Django hits the
DB separately for each row — same N+1 problem. Fix is to add
list_select_related = True on the ModelAdmin. This tells Django to do
a JOIN when fetching the list so all related data comes in one query.

Third thing is search. Django admin search uses LIKE '%keyword%' by
default. The wildcard at the start means the database can't use any
index — it scans every row. For 500k records that's painful. Fix is
to add a database index on the fields you search on, and if you need
full text search use SearchVector from django.contrib.postgres.search
instead of the default LIKE behaviour.

---

### Question B — Pagination Trade-offs

Offset pagination works like this — give me 20 records, skip the first
10000. Simple to implement and easy for the frontend to jump to any
page. The problem is the database still has to scan and skip those
10000 rows every time. At page 500 of a mobile infinite scroll that's
a serious performance hit.

The bigger problem is data mutation. If someone places a new order
while a user is scrolling, all the offsets shift by one. The user ends
up seeing a duplicate record or missing one entirely. On a busy
platform during a flash sale this happens constantly.

Cursor pagination fixes both. Instead of saying "skip 10000" you say
"give me records where id is greater than the last one I saw". The
database uses the index to jump straight there — no scanning. Fast
regardless of how deep you are in the list.

The trade off is you can't jump to page 50 directly. You can only go
forward or backward from where you are. For mobile infinite scroll
that's fine — users only scroll forward anyway. For an admin dashboard
where someone wants to jump to a specific page, offset makes more
sense.

I'd use cursor for mobile infinite scroll on high traffic data and
offset for internal tools or reports where jumping to a specific page
matters more than performance.