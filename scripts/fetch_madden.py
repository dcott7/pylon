from datetime import date, datetime
import requests
import sqlite3
from typing import Any, Dict, List, Optional
import logging
import os


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
DB_PATH = os.path.join(DATA_DIR, "football.db")


BASE_URL: str = "https://drop-api.ea.com/rating/madden-nfl"
LIMIT: int = 100
WEEKS: List[str] = [f"{i + 1}-week-{i}" for i in range(1, 2)] + [
    "20-wild-card-round",
    "21-divisional-round",
    "22-conference-championship-round",
    "23-super-bowl",
]


def ea_to_espn_corrections(
    norm_first: str, norm_last: str, dob: date
) -> tuple[str, str, date]:
    """Correct known EA mismatches (names or DOBs)."""
    corrections = {
        # (EA SOURCE) : (ESPN SOURCE)
        # EA wrong DOB
        ("creed", "humphrey", dob): ("creed", "humphrey", date(1999, 6, 28)),
        ("isiah", "pacheco", dob): ("isiah", "pacheco", date(1999, 3, 2)),
        ("trevon", "diggs", dob): ("trevon", "diggs", date(1998, 9, 20)),
        ("kolton", "miller", dob): ("kolton", "miller", date(1995, 10, 9)),
        ("brian", "robinson jr", dob): ("brian", "robinson jr", date(1999, 3, 22)),
        ("jakobi", "meyers", dob): ("jakobi", "meyers", date(1996, 11, 9)),
        ("corey", "bojorquez", dob): ("corey", "bojorquez", date(1996, 9, 13)),
        ("chase", "young", dob): ("chase", "young", date(1999, 4, 14)),
        ("cole", "holcomb", dob): ("cole", "holcomb", date(1996, 7, 30)),
        ("jk", "scott", dob): ("jk", "scott", date(1995, 10, 30)),
        ("kaden", "elliss", dob): ("kaden", "elliss", date(1995, 7, 10)),
        ("thomas", "morstead", dob): ("thomas", "morstead", date(1986, 3, 8)),
        ("mike", "danna", dob): ("mike", "danna", date(1997, 12, 4)),
        ("bj", "hill", dob): ("bj", "hill", date(1995, 4, 20)),
        ("jarran", "reed", dob): ("jarran", "reed", date(1992, 12, 16)),
        ("pete", "werner", dob): ("pete", "werner", date(1999, 6, 5)),
        ("sione", "takitaki", dob): ("sione", "takitaki", date(1995, 6, 8)),
        ("tyler", "nubin", dob): ("tyler", "nubin", date(2001, 6, 14)),
        ("will", "reichard", dob): ("will", "reichard", date(2001, 1, 9)),
        ("terrion", "arnold", dob): ("terrion", "arnold", date(2003, 3, 22)),
        ("keeanu", "benton", dob): ("keeanu", "benton", date(2001, 7, 17)),
        ("justin", "watson", dob): ("justin", "watson", date(1996, 4, 4)),
        ("akayleb", "evans", dob): ("akayleb", "evans", date(1999, 6, 22)),
        ("kenneth", "murray jr", dob): ("kenneth", "murray jr", date(1998, 11, 16)),
        ("pharaoh", "brown", dob): ("pharaoh", "brown", date(1994, 5, 4)),
        ("tyler", "guyton", dob): ("tyler", "guyton", date(2001, 6, 11)),
        ("mario", "edwards jr", dob): ("mario", "edwards jr", date(1994, 1, 25)),
        ("rodney", "thomas ii", dob): ("rodney", "thomas ii", date(1998, 6, 26)),
        ("bryce", "young", dob): ("bryce", "young", date(2001, 7, 25)),
        ("bub", "means", dob): ("bub", "means", date(2001, 1, 10)),
        ("sean", "rhyan", dob): ("sean", "rhyan", date(2000, 9, 15)),
        ("carson", "steele", dob): ("carson", "steele", date(2002, 10, 21)),
        ("jalen", "coker", dob): ("jalen", "coker", date(2001, 10, 30)),
        ("malik", "washington", dob): ("malik", "washington", date(2001, 1, 4)),
        ("mohamed", "kamara", dob): ("mohamed", "kamara", date(1999, 5, 29)),
        ("trenton", "gill", dob): ("trenton", "gill", date(1999, 1, 1)),
        ("devaughn", "vele", dob): ("devaughn", "vele", date(1997, 12, 12)),
        ("jeremiah", "ledbetter", dob): ("jeremiah", "ledbetter", date(1994, 6, 2)),
        ("jihad", "ward", dob): ("jihad", "ward", date(1994, 5, 11)),
        ("marcellas", "dial", dob): ("marcellas", "dial jr", dob),
        ("marlon", "tuipulotu", dob): ("marlon", "tuipulotu", date(1999, 5, 31)),
        ("josh", "hayes", dob): ("josh", "hayes", date(1999, 4, 24)),
        ("kitan", "oladapo", dob): ("kitan", "oladapo", date(2000, 10, 10)),
        ("raheem", "blackshear", dob): ("raheem", "blackshear", date(1998, 6, 5)),
        ("tre", "tomlinson", dob): ("tre", "tomlinson", date(2001, 1, 2)),
        ("chris", "collier", dob): ("chris", "collier", date(2000, 3, 24)),
        ("hunter", "nourzad", dob): ("hunter", "nourzad", date(2000, 11, 26)),
        ("jon", "gaines ii", dob): ("jon", "gaines ii", date(1999, 5, 24)),
        ("malik", "heath", dob): ("malik", "heath", date(2000, 3, 31)),
        ("byron", "cowart", dob): ("byron", "cowart", date(1996, 5, 20)),
        ("logan", "bruss", dob): ("logan", "bruss", date(1999, 10, 6)),
        ("will", "mallory", dob): ("will", "mallory", date(1999, 6, 22)),
        ("malik", "herring", dob): ("malik", "herring", date(1997, 11, 9)),
        ("ochaun", "mathis", dob): ("ochaun", "mathis", date(1999, 1, 8)),
        ("patrick", "johnson", dob): ("patrick", "johnson", date(1998, 1, 10)),
        ("jake", "haener", dob): ("jake", "haener", date(1999, 3, 10)),
        ("easton", "stick", dob): ("easton", "stick", date(1995, 9, 15)),
        ("trevor", "denbow", dob): ("trevor", "denbow", date(1998, 8, 26)),
        ("stone", "smartt", dob): ("stone", "smartt", date(1998, 10, 4)),
        ("trent", "sieg", dob): ("trent", "sieg", date(1995, 5, 19)),
        ("ty'ron", "hopper", dob): ("ty'ron", "hopper", date(2001, 4, 26)),
        ("jc", "latham", dob): ("jc", "latham", date(2003, 2, 8)),
        ("dj", "turner ii", dob): ("dj", "turner ii", date(2000, 11, 9)),
        ("mike", "boone", dob): ("mike", "boone", date(1995, 6, 30)),
        ("brenden", "bates", dob): ("brenden", "bates", date(1999, 10, 16)),
        ("jonathan", "ford", dob): ("jonathan", "ford", date(1998, 9, 29)),
        ("anthony", "pittman", dob): ("anthony", "pittman", date(1996, 11, 24)),
        ("elijah", "garcia", dob): ("elijah", "garcia", date(1998, 3, 11)),
        ("zach", "cunningham", dob): ("zach", "cunningham", date(1994, 12, 2)),
        # Name mismatches
        ("patrick", "surtain ii", dob): ("pat", "surtain ii", dob),
        ("aaron", "jones", dob): ("aaron", "jones sr", dob),
        ("dj", "reed jr", dob): ("dj", "reed", dob),
        ("tariq", "woolen", dob): ("riq", "woolen", dob),
        ("da'ron", "payne", dob): ("daron", "payne", dob),
        ("joey", "porter", dob): ("joey", "porter jr", dob),
        ("kyle", "pitts", dob): ("kyle", "pitts sr", dob),
        ("marquise", "brown", dob): ("hollywood", "brown", dob),
        ("jermaine", "johnson ii", dob): ("jermaine", "johnson", dob),
        ("cornelius", "lucas iii", dob): ("cornelius", "lucas", dob),
        ("isaiah", "rodgers sr", dob): ("isaiah", "rodgers", dob),
        ("allen", "robinson ii", dob): ("allen", "robinson", dob),
        ("maurice", "hurst", dob): ("maurice", "hurst ii", dob),
        ("mekhi", "becton sr", dob): ("mekhi", "becton", dob),
        ("dj", "chark jr", dob): ("dj", "chark", dob),
        ("josh", "uche", dob): ("joshua", "uche", dob),
        ("calvin", "austin", dob): ("calvin", "austin iii", dob),
        ("aj", "jackson", dob): ("alaric", "jackson", dob),
        ("chigoziem", "okonkwo", dob): ("chig", "okonkwo", dob),
        ("darrell", "baker", dob): ("darrell", "baker jr", dob),
        ("lawrence", "guy sr", dob): ("lawrence", "guy", dob),
        ("nyheim", "hines", dob): ("nyheim", "miller-hines", dob),
        ("gardner", "minshew ii", dob): ("gardner", "minshew", dob),
        ("anthony", "richardson", dob): ("anthony", "richardson sr", dob),
        ("scott", "miller", dob): ("scotty", "miller", dob),
        ("james", "houston iv", dob): ("james", "houston", dob),
        ("andrew", "booth jr", dob): ("andrew", "booth", dob),
        ("robert", "jones", dob): ("rob", "jones", dob),
        ("tj", "slaton", dob): ("tj", "slaton jr", dob),
        ("albert", "okwuegbunam", dob): ("albert", "okwuegbunam jr", dob),
        ("trayvon", "mullen jr", dob): ("trayvon", "mullen", dob),
        ("christopher", "smith ii", dob): ("chris", "smith ii", dob),
        ("olusegun", "oluwatimi", dob): ("olu", "oluwatimi", dob),
        ("rakeem", "nunez-roches sr", dob): ("rakeem", "nunez-roches", dob),
        ("anthony", "johnson jr", dob): ("anthony", "johnson", dob),
        ("john", "ridgeway", dob): ("john", "ridgeway iii", dob),
        ("nathan", "thomas", dob): ("nate", "thomas", dob),
        ("warren", "mcclendon", dob): ("warren", "mcclendon jr", dob),
        ("brenton", "cox", dob): ("brenton", "cox jr", dob),
        ("zachary", "thomas", dob): ("zach", "thomas", dob),
        ("john", "shenker", dob): ("john samuel", "shenker", dob),
        ("patrick", "taylor", dob): ("patrick", "taylor jr", dob),
        ("chris", "roland-wallace", dob): ("christian", "roland-wallace", dob),
        ("leroy", "watson", dob): ("leroy", "watson iv", dob),
        ("matthew", "orzech", dob): ("matt", "orzech", dob),
        ("darius", "slay jr", dob): ("darius", "slay", dob),
        ("camryn", "bynum", dob): ("cam", "bynum", dob),
        ("dan", "moore", dob): ("dan", "moore jr", dob),
        ("mj", "stewart jr", dob): ("mj", "stewart", dob),
        ("ernest", "jones", dob): ("ernest", "jones iv", dob),
        ("olumuyiwa", "fashanu", dob): ("olu", "fashanu", dob),
        ("antonio", "hamilton", dob): ("antonio", "hamilton sr", dob),
        ("dante", "fowler", dob): ("dante", "fowler jr", dob),
        ("julius", "brents", dob): ("juju", "brents", dob),
        ("cordale", "flott", dob): ("cor'dale", "flott", dob),
        ("boogie", "basham jr", dob): ("boogie", "basham", dob),
        ("andru", "phillips", dob): ("dru", "phillips", dob),
        ("takkarist", "mckinley", dob): ("takk", "mckinley", dob),
        ("deantre", "prince", dob): ("de'antre", "prince", dob),
        ("tre'viushodges-tomlinson", dob): ("tre", "tomlinson", date(2000, 1, 10)),
        ("andrew", "ogletree", dob): ("drew", "ogletree", dob),
        ("geron", "christian sr", dob): ("geron", "christian", dob),
        ("doug", "kramer", dob): ("doug", "kramer jr", dob),
        ("mecole", "hardman jr", dob): ("mecole", "hardman", dob),
        ("jartavius", "martin", dob): ("quan", "martin", dob),
        ("john", "metchie", dob): ("john", "metchie iii", dob),
        ("greg", "stroman", dob): ("greg", "stroman jr", dob),
        ("joe", "noteboom", dob): ("joseph", "noteboom", dob),
        ("jacob", "hummel", dob): ("jake", "hummel", dob),
    }
    return corrections.get((norm_first, norm_last, dob), (norm_first, norm_last, dob))


def normalize_madden_birthdate(raw: Optional[str]) -> Optional[str]:
    """
    Converts Madden birthdate like '8/29/02' to '2002-08-29'
    """
    if not raw:
        return None

    try:
        dt = datetime.strptime(raw, "%m/%d/%y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def init_madden_tables(conn: sqlite3.Connection):
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS madden_players (
            madden_id INTEGER PRIMARY KEY,
            espn_id INTEGER,
            first_name TEXT,
            last_name TEXT,
            birthdate TEXT,
            height INTEGER,
            weight INTEGER,
            years_pro INTEGER,
            college TEXT,
            handedness TEXT,
            FOREIGN KEY (espn_id) REFERENCES athletes(espn_id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS madden_ratings (
            madden_id INTEGER,
            iteration_id TEXT,
            overall_rating INTEGER,
            team_id INTEGER,
            position_id INTEGER,
            PRIMARY KEY (madden_id, iteration_id),
            FOREIGN KEY (madden_id) REFERENCES madden_players(madden_id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS madden_abilities (
            madden_id INTEGER,
            iteration_id TEXT,
            ability_id INTEGER,
            ability_label TEXT,
            ability_type TEXT,
            PRIMARY KEY (madden_id, iteration_id, ability_id)
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS madden_stat_types (
            stat_key TEXT PRIMARY KEY,
            description TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS madden_player_stats (
            madden_id INTEGER,
            iteration_id TEXT,
            stat_key TEXT,
            stat_value INTEGER,
            stat_diff INTEGER,
            PRIMARY KEY (madden_id, iteration_id, stat_key)
        )
        """
    )

    conn.commit()


def load_madden_player(
    cur: sqlite3.Cursor,
    item: Dict[str, Any],
    espn_id: Any,
):
    cur.execute(
        """
        INSERT OR IGNORE INTO madden_players (
            madden_id, espn_id,
            first_name, last_name, birthdate,
            height, weight, years_pro,
            college, handedness
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item["id"],
            espn_id,
            item.get("firstName"),
            item.get("lastName"),
            item.get("birthdate"),
            item.get("height"),
            item.get("weight"),
            item.get("yearsPro"),
            item.get("college"),
            item.get("handedness"),
        ),
    )


def load_madden_rating(cur: sqlite3.Cursor, item: Dict[str, Any]):
    cur.execute(
        """
        INSERT OR REPLACE INTO madden_ratings (
            madden_id,
            iteration_id,
            overall_rating,
            team_id,
            position_id
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            item["id"],
            item["iteration"]["id"],
            item.get("overallRating"),
            item.get("team", {}).get("id"),
            item.get("position", {}).get("id"),
        ),
    )


def load_madden_abilities(cur: sqlite3.Cursor, item: Dict[str, Any]):
    for ability in item.get("playerAbilities", []):
        cur.execute(
            """
            INSERT OR IGNORE INTO madden_abilities (
                madden_id,
                iteration_id,
                ability_id,
                ability_label,
                ability_type
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                item["id"],
                item["iteration"]["id"],
                ability["id"],
                ability["label"],
                ability["type"]["label"],
            ),
        )


def fetch_week_data(week_iteration: str) -> List[Dict[str, Any]]:
    """Fetches all player ratings for a specific week using pagination."""
    items: List[Dict[str, Any]] = []
    offset: int = 0

    while True:
        params: Dict[str, Any] = {
            "limit": LIMIT,
            "offset": offset,
            "iteration": week_iteration,
        }
        response = requests.get(BASE_URL, params=params)
        logger.info(f"Requesting: {response.url} → Status Code: {response.status_code}")

        if response.status_code != 200:
            logger.warning(
                f"Failed to fetch data for {week_iteration} with offset {offset}"
            )
            break

        data = response.json()
        page_items = data.get("items", [])
        items.extend(page_items)

        total_items = data.get("totalItems", 0)
        offset += LIMIT

        if offset >= total_items:
            break

    return items


def load_madden_stats(
    cur: sqlite3.Cursor,
    item: Dict[str, Any],
):
    stats = item.get("stats", {})
    iteration_id = item["iteration"]["id"]
    madden_id = item["id"]

    for stat_key, stat_data in stats.items():
        value = stat_data.get("value")
        diff = stat_data.get("diff")

        # Skip non-numeric stats (e.g. runningStyle)
        if not isinstance(value, (int, float)):
            continue

        # Register stat type (idempotent)
        cur.execute(
            """
            INSERT OR IGNORE INTO madden_stat_types (stat_key)
            VALUES (?)
            """,
            (stat_key,),
        )

        # Insert stat value
        cur.execute(
            """
            INSERT OR REPLACE INTO madden_player_stats (
                madden_id,
                iteration_id,
                stat_key,
                stat_value,
                stat_diff
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                madden_id,
                iteration_id,
                stat_key,
                int(value),
                int(diff) if diff is not None else None,
            ),
        )


def fetch_all_ratings() -> List[Dict[str, Any]]:
    """Fetches all player ratings across all weeks."""
    all_items: List[Dict[str, Any]] = []
    for week in WEEKS:
        print(f"Fetching data for {week}...")
        week_items = fetch_week_data(week)
        all_items.extend(week_items)
    return all_items


def map_to_espn_athlete(cur: sqlite3.Cursor, madden_player: Dict[str, Any]) -> Any:
    raw_first = madden_player.get("firstName", "").strip()
    raw_last = madden_player.get("lastName", "").strip()
    raw_birth = madden_player.get("birthdate")

    normalized_dob = normalize_madden_birthdate(raw_birth)
    if not normalized_dob:
        logger.warning(
            "No valid birthdate for Madden player: %s %s", raw_first, raw_last
        )
        return None

    dob_obj = datetime.strptime(normalized_dob, "%Y-%m-%d").date()

    # Normalize for matching
    norm_first = raw_first.lower()
    norm_last = raw_last.lower()

    # Apply EA→ESPN corrections
    corr_first, corr_last, corr_dob = ea_to_espn_corrections(
        norm_first, norm_last, dob_obj
    )

    corr_first = corr_first.replace(".", "")
    corr_last = corr_last.replace(".", "")

    # Convert corrected DOB to string
    dob_str = corr_dob.isoformat()

    cur.execute(
        """
        SELECT espn_id FROM athletes
        WHERE lower(replace(first_name, ".", "")) = ?
          AND lower(replace(last_name, ".", "")) = ?
          AND substr(date_of_birth, 1, 10) = ?
        """,
        (corr_first, corr_last, dob_str),
    )

    rows = cur.fetchall()

    if len(rows) < 1:
        logger.warning(
            "No matching ESPN athlete for Madden player: %s %s - %s",
            madden_player["firstName"],
            madden_player["lastName"],
            normalized_dob,
        )
        return None

    if len(rows) > 1:
        logger.warning(
            "Multiple matching ESPN athletes for Madden player: %s %s - %s",
            madden_player["firstName"],
            madden_player["lastName"],
            normalized_dob,
        )
        logger.warning("Matches: %s", rows)
        return None

    return rows[0][0]


def load_all_madden_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    init_madden_tables(conn)

    all_items = fetch_all_ratings()
    logger.info("Fetched %s total Madden records", len(all_items))

    for item in all_items:
        espn_id = map_to_espn_athlete(cur, item)

        load_madden_player(cur, item, espn_id)
        load_madden_rating(cur, item)
        load_madden_abilities(cur, item)
        load_madden_stats(cur, item)

    conn.commit()
    conn.close()
    logger.info("Madden data load complete")


if __name__ == "__main__":
    load_all_madden_data()
