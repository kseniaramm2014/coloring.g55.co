<?php
// app/page_pre.php
require_once 'common.php';

$index = load_site_index();
$site = $index['site'];
$categories = get_categories_sorted($index);

if (!isset($_GET['id'], $_GET['c'])) {
  header('Location: /', true, 302);
  exit;
}

$id = clean_slug($_GET['id']);
$cid = clean_slug($_GET['c']);

if ($id === '' || $cid === '') {
  header('Location: /', true, 302);
  exit;
}

$cat = null;
foreach ($categories as $c) {
  if ($c['id'] === $cid) {
    $cat = $c;
    break;
  }
}

if ($cat === null) {
  header('Location: /', true, 302);
  exit;
}

list($_, $pages) = load_category_pages($cid);

$page = null;
$pageIndex = -1;

for ($i = 0; $i < count($pages); $i++) {
  if (($pages[$i]['id'] ?? '') === $id) {
    $page = $pages[$i];
    $pageIndex = $i;
    break;
  }
}

if ($page === null) {
  header('Location: /', true, 302);
  exit;
}

$pageTitle = $page['title'];
$title = $pageTitle;

$metaDesc = $page['description'];
$canonical = 'https://coloring.g55.co/page.php?id=' . rawurlencode($id) . '&c=' . rawurlencode($cid);
$imageSrc = '/categories/' . $cid . '/' . $page['id'] . '.png';

$h1 = $pageTitle;
$desc = $page['description'];

$prevPage = null;
$nextPage = null;
$prevUrl = null;
$nextUrl = null;

if ($pageIndex !== -1) {
  if ($pageIndex > 0) {
    $prevPage = $pages[$pageIndex - 1];
    $prevUrl = '/page.php?id=' . rawurlencode($prevPage['id']) . '&c=' . rawurlencode($cid);
  }

  if ($pageIndex < count($pages) - 1) {
    $nextPage = $pages[$pageIndex + 1];
    $nextUrl = '/page.php?id=' . rawurlencode($nextPage['id']) . '&c=' . rawurlencode($cid);
  }
}

$similar = [];

if ($pageIndex !== -1) {
    $used = [$id => true];
    $radius = 1;
    $max = count($pages);

    while (count($similar) < 6 && (($pageIndex - $radius) >= 0 || ($pageIndex + $radius) < $max)) {
        $left = $pageIndex - $radius;
        $right = $pageIndex + $radius;

        if ($left >= 0) {
            $p = $pages[$left];
            $pid = $p['id'] ?? '';
            if ($pid !== '' && !isset($used[$pid])) {
                $similar[] = $p;
                $used[$pid] = true;
                if (count($similar) >= 6) {
                    break;
                }
            }
        }

        if ($right < $max) {
            $p = $pages[$right];
            $pid = $p['id'] ?? '';
            if ($pid !== '' && !isset($used[$pid])) {
                $similar[] = $p;
                $used[$pid] = true;
                if (count($similar) >= 6) {
                    break;
                }
            }
        }

        $radius++;
    }
}

$moreText = 'More ' . $cat['name'] . ' Coloring Pages';
$moreHref = '/?c=' . rawurlencode($cid);
$moreTitle = 'Similar ' . $cat['name'] . ' Coloring Pages';