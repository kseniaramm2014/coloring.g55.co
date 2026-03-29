<?php
// app/index_pre.php
require_once 'common.php';

$index = load_site_index();
$site = $index['site'];
$categories = get_categories_sorted($index);
$grouped = get_categories_clustered($index);

$catMap = [];
foreach ($categories as $c) {
  $catMap[$c['id']] = $c;
}

function category_pages_pagination(array $allPages, int $perPage = 60, string $pageParam = 'p'): array {
  $totalItems = count($allPages);
  $totalPages = max(1, (int) ceil($totalItems / $perPage));

  $page = 1;
  if (isset($_GET[$pageParam])) {
    $page = (int) $_GET[$pageParam];
    if ($page < 1) $page = 1;
  }
  if ($page > $totalPages) $page = $totalPages;

  $offset = ($page - 1) * $perPage;
  $items = array_slice($allPages, $offset, $perPage);

  return [
    'page' => $page,
    'per_page' => $perPage,
    'total_items' => $totalItems,
    'total_pages' => $totalPages,
    'items' => $items,
    'has_prev' => $page > 1,
    'has_next' => $page < $totalPages,
  ];
}

function category_url(string $cid, ?int $p = null): string {
  if ($p === null || $p <= 1) return 'https://coloring.g55.co/?c=' . rawurlencode($cid);
  return 'https://coloring.g55.co/?c=' . rawurlencode($cid) . '&p=' . (int) $p;
}

$hasC = isset($_GET['c']);

if ($hasC) {
  $cid = clean_slug($_GET['c']);
  if ($cid === '' || !isset($catMap[$cid])) {
    header('Location: /', true, 302);
    exit;
  }

  $cat = $catMap[$cid];
  $currentCluster = find_cluster_for_category($grouped, $cid);
  list($_, $pages) = load_category_pages($cid);

  $pager = category_pages_pagination($pages, 60, 'p');
  $pageNum = $pager['page'];

  $canonical = category_url($cid);
  $prevUrl = $pager['has_prev'] ? category_url($cid, $pageNum - 1) : null;
  $nextUrl = $pager['has_next'] ? category_url($cid, $pageNum + 1) : null;

  $gridItems = [];
  foreach ($pager['items'] as $p) {
    $gridItems[] = [
      'id' => $p['id'],
      'title' => $p['title'],
      'image' => '/categories/' . $cid . '/' . $p['id'] . '.png',
      'category' => $cid
    ];
  }

  $count = count($pages);
  $h1 = ($count > 0 ? number_format($count) . ' ' : '') . $cat['name'] . ' Coloring Pages';
  if ($pageNum > 1) $h1 .= ' Page ' . $pageNum;

  $desc = $cat['description'];

  $title = $h1;
  $metaDesc = trim(preg_replace('/\s+/', ' ', preg_split('/key features/i', strip_tags($desc))[0]));
} else {
  $totalCount = 0;
  $gridItems = [];

  foreach ($categories as $c) {
    $catId = $c['id'];

    list($_, $pages) = load_category_pages($catId);
    $totalCount += count($pages);

    $newest = newest_page($pages);
    $gridItems[] = [
      'id' => $newest['id'],
      'title' => $newest['title'],
      'image' => '/categories/' . $catId . '/' . $newest['id'] . '.png',
      'category' => $catId
    ];
  }

  $h1 = ($totalCount > 0 ? number_format($totalCount) . ' ' : '') . $site['title'];
  $desc = $site['description'];

  $title = $h1;
  $metaDesc = strip_tags($desc);
  $canonical = 'https://coloring.g55.co/';
}
