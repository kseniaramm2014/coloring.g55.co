<?php require_once 'app/index_pre.php'; ?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title><?php echo h($title); ?></title>
<meta name="description" content="<?php echo h($metaDesc); ?>">
<link rel="canonical" href="<?php echo h($canonical); ?>">
<?php include 'head.php'; ?>
</head>

<body>
<?php include 'header.php'; ?>
<main>
<article>
<div class="title">
<h1><?php echo h($h1); ?></h1>
<p><?php echo $desc; ?></p>
</div>
<div class="grid">
<?php foreach ($gridItems as $it): ?>
<a class="thumbnail" href="/page.php?id=<?php echo rawurlencode($it['id']); ?>&c=<?php echo rawurlencode($it['category']); ?>">
<img src="<?php echo h('/categories/' . $it['category'] . '/' . $it['id'] . '.png'); ?>" alt="<?php echo h(makeImageAlt($it['id'])); ?>">
<span><?php echo h($it['title']); ?></span>
</a>
<?php endforeach; ?>
</div>
</article>
<?php if (!empty($pager) && $pager['total_pages'] > 1): ?>
<nav class="pagination">
<?php if ($pager['has_prev']): ?>
<a class="tag" href="<?php echo h($prevUrl) ?>">Prev Page</a>
<?php endif; ?>
<?php if ($pager['has_next']): ?>
<a class="tag" href="<?php echo h($nextUrl) ?>">Next Page</a>
<?php endif; ?>
</nav>
<?php endif; ?>
<?php include 'footer.php'; ?>
</body>
</html>