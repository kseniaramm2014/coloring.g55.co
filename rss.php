<?php
require_once 'app/index_pre.php';
$pages = array_slice($pages, 0, 50);
header('Content-Type: application/rss+xml; charset=utf-8');
echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
<title><?php echo h($cat['name']); ?> Coloring Pages</title>
<link><?php echo h($canonical); ?></link>
<description><?php echo h(strip_tags($metaDesc)); ?></description>
<?php foreach ($pages as $p): ?>
<item>
<title><?php echo h($p['title']); ?></title>
<link>https://coloring.g55.co/page.php?id=<?php echo rawurlencode($p['id']); ?>&amp;c=<?php echo rawurlencode($cid); ?></link>
<guid isPermaLink="true">https://coloring.g55.co/page.php?id=<?php echo rawurlencode($p['id']); ?>&amp;c=<?php echo rawurlencode($cid); ?></guid>
<description><?php echo h($p['description']); ?></description>
<media:content url="https://coloring.g55.co/categories/<?php echo rawurlencode($cid); ?>/<?php echo rawurlencode($p['id']); ?>.png" medium="image" type="image/png" />
</item>
<?php endforeach; ?>
</channel>
</rss>
