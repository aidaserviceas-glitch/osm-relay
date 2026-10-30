# osm-relay

Small helper that runs public OpenStreetMap (Overpass) lookups on a schedule and hands the results back to our Cloudflare workers, because the public Overpass mirrors block Cloudflare IPs. Only public map data about businesses. One query at a time, with pauses, to be polite to the volunteer-run Overpass servers.
