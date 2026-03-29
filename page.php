<?php require_once 'app/page_pre.php'; ?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?php echo h($title); ?></title>
<meta name="description" content="<?php echo h($metaDesc); ?>">
<link rel="canonical" href="<?php echo h($canonical); ?>">
<link rel="image_src" href="<?php echo h($imageSrc); ?>">
<?php include 'head.php'; ?>
</head>

<body>
<?php include 'header.php'; ?>
<main>
<article class="content">
<section class="description">
<h1><?php echo h($h1); ?></h1>
<p><?php echo h($desc); ?></p>
<a class="tag save" href="https://www.pinterest.com/pin/create/button/?url=<?php echo rawurlencode($canonical); ?>&description=<?php echo rawurlencode($desc); ?>" target="_blank">Save to Pinterest</a>
<button class="tag print" onclick="window.print();">Print</button>
<a class="tag download" href="<?php echo h($imageSrc); ?>" download>Download</a>
<a class="tag more" href="<?php echo h($moreHref); ?>"><?php echo h($moreText); ?></a>
</section>
<img class="page" onclick="this.requestFullscreen();" src="<?php echo h($imageSrc); ?>" alt="<?php echo h(makeImageAlt($page['id'])); ?>">
</article>
<nav class="pagination">
<?php if ($prevUrl): ?>
<a class="tag" href="<?php echo h($prevUrl) ?>">Prev Page</a>
<?php endif; ?>
<?php if ($nextUrl): ?>
<a class="tag" href="<?php echo h($nextUrl) ?>">Next Page</a>
<?php endif; ?>
</nav>
<?php if (!empty($currentCluster)): ?>
<nav class="cluster">
<h2>Explore <?php echo h($currentCluster[0]['name']) ?> Coloring Pages</h2>
<ul class="categories">
<?php foreach ($currentCluster as $c): ?>
<li><a class="tag" href="/?c=<?php echo rawurlencode($c['id']); ?>"><?php echo h($c['name']); ?></a></li>
<?php endforeach; ?>
</ul>
</nav>
<?php endif; ?>
<aside>
<h2><?php echo h($moreTitle); ?></h2>
<div class="grid">
<?php foreach ($similar as $p): ?>
<a class="thumbnail" href="/page.php?id=<?php echo rawurlencode($p['id']); ?>&c=<?php echo rawurlencode($cid); ?>">
<img src="<?php echo h('/categories/' . $cid . '/' . $p['id'] . '.png'); ?>" alt="<?php echo h(makeImageAlt($p['id'])); ?>">
<span><?php echo h($p['title']); ?></span>
</a>
<?php endforeach; ?>
</div>
</aside>
</main>
<?php include 'footer.php'; ?>
</body>
</html>