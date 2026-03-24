<nav>
<h2>Browse More Coloring Pages</h2>
<ul class="categories">
<?php foreach ($categories as $c): ?>
<li><a class="tag" href="/?c=<?php echo rawurlencode($c['id']); ?>"><?php echo h($c['name']); ?></a></li>
<?php endforeach; ?>
</ul>
</nav>
</main>
<footer>
<div>
<span>&#169; <?php echo date('Y'); ?> Coloring.G55.CO</span>
<a href="/privacy-policy.php">Privacy Policy</a>
</div>
<div>
<a href="https://g55.co/">Online Games</a>
</div>
</footer>
