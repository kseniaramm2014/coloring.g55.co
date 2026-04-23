<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

$BASE_DIR = __DIR__;
$APP_DIR = $BASE_DIR . DIRECTORY_SEPARATOR . 'app';
$CATEGORIES_DIR = $BASE_DIR . DIRECTORY_SEPARATOR . 'categories';

function qs(string $k, string $default = ''): string {
  return isset($_GET[$k]) ? trim((string)$_GET[$k]) : $default;
} 
function qb(string $k, bool $default = false): bool {
  if (!isset($_GET[$k])) return $default;
  $v = strtolower(trim((string)$_GET[$k]));
  return in_array($v, ['1','true','yes','on'], true);
}

function json_out(array $payload, int $code = 200): void {
  http_response_code($code);
  echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT);
  exit;
}

function load_lines(string $path): array {
  if (!is_file($path)) return [];
  $lines = file($path, FILE_IGNORE_NEW_LINES);
  if (!is_array($lines)) return [];
  $out = [];
  foreach ($lines as $line) {
    $s = trim((string)$line);
    if ($s === '') continue;
    if (str_starts_with($s, '#')) continue;
    $out[] = $s;
  }
  return $out;
}

function load_style(string $style_file): string {
  $lines = load_lines($style_file);
  $s = trim(implode(' ', $lines));
  $s = preg_replace('/\s{2,}/', ' ', $s ?? '') ?? '';
  return trim($s);
}

function strip_leading_article(string $s): string {
  $s = trim($s);
  $s = preg_replace('/^(a|an|the)\s+/i', '', $s) ?? $s;
  return trim($s);
}

function format_title(string $s): string {
  $s = trim($s);
  $s = preg_replace('/\s{2,}/', ' ', $s ?? '') ?? $s;
  return ucwords(strtolower($s));
}

function slugify(string $s): string {
  $s = strtolower(trim($s));
  $s = preg_replace('/[^\p{L}\p{N}]+/u', '-', $s) ?? $s;
  $s = preg_replace('/-+/', '-', $s) ?? $s;
  $s = trim($s, '-');
  return $s !== '' ? $s : 'item';
}

function clean_sentence(string $s): string {
  $s = trim(preg_replace('/\s{2,}/', ' ', trim($s)) ?? '');
  $s = trim($s, " ,");
  if ($s === '') return '';
  if (!str_ends_with($s, '.')) $s .= '.';
  return $s;
}

function render_template(string $line, string $scene): string {
  return str_replace('{scene}', $scene, $line);
}

function build_title(array $parts): string {
  $character = strip_leading_article((string)$parts['character']);
  $action = trim((string)$parts['action']);
  $env = trim((string)$parts['environment']);
  $base = trim(preg_replace('/\s{2,}/', ' ', "$character $action $env") ?? '');
  return 'Free Printable ' . format_title($base) . ' Coloring Page for Kids';
}

function build_id(array $parts): string {
  $character = strip_leading_article((string)$parts['character']);
  $action = trim((string)$parts['action']);
  $env = trim((string)$parts['environment']);
  $base = trim(preg_replace('/\s{2,}/', ' ', "$character $action $env coloring page") ?? '');
  return slugify($base);
}

function build_prompt(array $parts, string $style): string {
  $core = trim(preg_replace('/\s{2,}/', ' ', $parts['character'] . ' ' . $parts['action'] . ' ' . $parts['environment']) ?? '');
  return 'Coloring page on white background, ' . $core . ', ' . rtrim($style, '.') . '.';
}

function build_description(array $parts, array $pools): string {
  $scene = trim(preg_replace('/\s{2,}/', ' ', $parts['character'] . ' ' . $parts['action'] . ' ' . $parts['environment']) ?? '');

  $patterns = [
    ['intro', 'usage', 'ease', 'benefit'],
    ['intro', 'usage', 'benefit', 'ease'],
    ['intro', 'ease', 'usage', 'benefit'],
    ['intro', 'ease', 'benefit', 'usage'],
    ['intro', 'benefit', 'usage', 'ease'],
    ['intro', 'benefit', 'ease', 'usage'],
  ];

  $pattern = $patterns[array_rand($patterns)];
  $sentences = [];

  foreach ($pattern as $k) {
    $line = $pools[$k][array_rand($pools[$k])];
    $sentences[] = clean_sentence(render_template($line, $scene));
  }

  return trim(implode(' ', array_filter($sentences)));
}

function ensure_dir(string $dir): void {
  if (is_dir($dir)) return;
  @mkdir($dir, 0755, true);
}

function sanitize_filename(string $name): string {
  $name = trim($name);
  $name = preg_replace('/[^a-zA-Z0-9\.\_\-]+/', '_', $name) ?? $name;
  $name = preg_replace('/_+/', '_', $name) ?? $name;
  $name = trim($name, '_');
  return $name !== '' ? $name : 'image';
}

function png_is_1bit(string $path): bool {
  if (!is_file($path)) return false;
  $info = @getimagesize($path);
  if (!is_array($info)) return false;
  if (($info['mime'] ?? '') !== 'image/png') return false;
  return isset($info['bits']) && (int)$info['bits'] === 1;
}

function convert_png_to_1bit_gd(string $path, int $threshold = 200): array {
  if (!extension_loaded('gd')) return ['ok' => false, 'error' => 'gd_not_loaded'];
  if (!is_file($path)) return ['ok' => false, 'error' => 'missing_input', 'path' => $path];

  // skip if already 1-bit to avoid overwriting converted files
  if (png_is_1bit($path)) return ['ok' => true, 'skipped' => true];

  $bytes = @file_get_contents($path);
  if ($bytes === false) return ['ok' => false, 'error' => 'read_failed', 'path' => $path];

  $src = @imagecreatefromstring($bytes);
  if (!$src) return ['ok' => false, 'error' => 'imagecreate_failed'];

  $w = imagesx($src);
  $h = imagesy($src);

  // palette image = 1-bit possible
  $dst = imagecreate($w, $h);
  if (!$dst) { imagedestroy($src); return ['ok' => false, 'error' => 'imagecreate_palette_failed']; }

  imagealphablending($dst, true);

  $white = imagecolorallocate($dst, 255, 255, 255);
  $black = imagecolorallocate($dst, 0, 0, 0);

  for ($y = 0; $y < $h; $y++) {
    for ($x = 0; $x < $w; $x++) {
      $rgba = imagecolorat($src, $x, $y);

      // alpha in GD is 0..127 (0 opaque, 127 fully transparent)
      $a7 = ($rgba >> 24) & 0x7F;
      $r = ($rgba >> 16) & 0xFF;
      $g = ($rgba >> 8) & 0xFF;
      $b = $rgba & 0xFF;

      // treat transparent as white
      if ($a7 >= 64) {
        imagesetpixel($dst, $x, $y, $white);
        continue;
      }

      $lum = (int)round(0.2126 * $r + 0.7152 * $g + 0.0722 * $b);
      imagesetpixel($dst, $x, $y, ($lum >= $threshold) ? $white : $black);
    }
  }

  $ok = @imagepng($dst, $path, 9);

  imagedestroy($src);
  imagedestroy($dst);

  if (!$ok) return ['ok' => false, 'error' => 'write_failed', 'path' => $path];

  return ['ok' => true, 'skipped' => false];
}

function gemini_generate_image(
  string $api_key,
  string $prompt,
  string $out_path,
  string $aspect_ratio = '2:3'
): array {
  $model = 'gemini-3.1-flash-image-preview';
  $url = 'https://generativelanguage.googleapis.com/v1beta/models/' . rawurlencode($model) . ':generateContent';

  $payload = [
    'contents' => [
      [
        'parts' => [
          ['text' => $prompt]
        ]
      ]
    ],
    'generationConfig' => [
      'responseModalities' => ['Image'],
      'imageConfig' => [
        'aspectRatio' => $aspect_ratio
      ]
    ]
  ];

  $ch = curl_init($url);
  curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER => [
      'Content-Type: application/json',
      'x-goog-api-key: ' . $api_key
    ],
    CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE),
    CURLOPT_TIMEOUT => 120,
  ]);

  $raw = curl_exec($ch);
  $err = curl_error($ch);
  $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
  curl_close($ch);

  if ($raw === false) return ['ok' => false, 'error' => 'curl_error', 'detail' => $err];
  if ($code < 200 || $code >= 300) return ['ok' => false, 'error' => 'http_error', 'status' => $code, 'detail' => $raw];

  $json = json_decode($raw, true);
  if (!is_array($json)) return ['ok' => false, 'error' => 'bad_json', 'detail' => $raw];

  $image_b64 = null;
  $parts = $json['candidates'][0]['content']['parts'] ?? [];
  foreach ($parts as $p) {
    if (isset($p['inlineData']['data'])) { $image_b64 = (string)$p['inlineData']['data']; break; }
    if (isset($p['inline_data']['data'])) { $image_b64 = (string)$p['inline_data']['data']; break; }
  }
  if (!$image_b64) return ['ok' => false, 'error' => 'no_image_in_response'];

  $bytes = base64_decode($image_b64, true);
  if ($bytes === false) return ['ok' => false, 'error' => 'base64_decode_failed'];

  ensure_dir(dirname($out_path));
  $ok = file_put_contents($out_path, $bytes);
  if ($ok === false) return ['ok' => false, 'error' => 'write_failed', 'path' => $out_path];

  return ['ok' => true];
}

function category_json_path(string $categories_dir, string $category_name): string {
  return $categories_dir . DIRECTORY_SEPARATOR . $category_name . '.json';
}

function read_category_json_file(string $path): array {
  if (!is_file($path)) return ['pages' => []];
  $raw = file_get_contents($path);
  if (!is_string($raw) || trim($raw) === '') return ['pages' => []];
  $data = json_decode($raw, true);
  if (!is_array($data)) return ['pages' => []];
  if (!isset($data['pages']) || !is_array($data['pages'])) $data['pages'] = [];
  return $data;
}

function read_category_json_locked($fp): array {
  rewind($fp);
  $raw = stream_get_contents($fp);
  $data = json_decode($raw ?: '{}', true);
  if (!is_array($data)) $data = [];
  if (!isset($data['pages']) || !is_array($data['pages'])) $data['pages'] = [];
  return $data;
}

function write_category_json_locked($fp, array $data): void {
  ftruncate($fp, 0);
  rewind($fp);
  fwrite($fp, str_replace("    ", "", json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT)));
  fflush($fp);
}

function prepend_unique_pages(string $path, array $pages_to_add): array {
  if (!is_file($path)) return ['ok' => false, 'error' => 'missing_category_json', 'path' => $path];

  $fp = fopen($path, 'c+');
  if (!$fp) return ['ok' => false, 'error' => 'open_failed', 'path' => $path];

  if (!flock($fp, LOCK_EX)) { fclose($fp); return ['ok' => false, 'error' => 'lock_failed', 'path' => $path]; }

  $data = read_category_json_locked($fp);

  $existing_ids = [];
  foreach ($data['pages'] as $p) {
    if (is_array($p) && isset($p['id'])) $existing_ids[(string)$p['id']] = true;
  }

  $clean_add = [];
  $added_ids = [];
  foreach ($pages_to_add as $p) {
    $id = (string)($p['id'] ?? '');
    if ($id === '') continue;
    if (isset($existing_ids[$id])) continue;
    $existing_ids[$id] = true;

    $added_ids[] = $id;

    $clean_add[] = [
      'id' => $id,
      'title' => (string)($p['title'] ?? ''),
      'description' => (string)($p['description'] ?? ''),
    ];
  }

  $data['pages'] = array_values(array_merge($clean_add, $data['pages']));

  write_category_json_locked($fp, $data);

  flock($fp, LOCK_UN);
  fclose($fp);

  return ['ok' => true, 'added' => count($clean_add), 'added_ids' => $added_ids];
}

$category = qs('c', '');
if ($category === '') json_out(['ok' => false, 'error' => 'missing_c_param'], 400);

$count = 1; // hardcoded: always generate exactly 1 page per request

$do_img = true; // images always generated per request
$dry = qb('dry', false);

$aspect_ratio = qs('ar', '2:3'); 

$skip_existing_img = true;

// always convert to 1-bit like python version
$ONEBIT_THRESHOLD = 200;

$api_key = qs('key', '');
if ($api_key === '') $api_key = (string)getenv('GEMINI_API_KEY');

$cat_dir = $CATEGORIES_DIR . DIRECTORY_SEPARATOR . $category;
if (!is_dir($cat_dir)) json_out(['ok' => false, 'error' => 'missing_category_dir', 'category' => $category], 404);

$characters = load_lines($cat_dir . DIRECTORY_SEPARATOR . 'characters.txt');
$actions = load_lines($CATEGORIES_DIR . DIRECTORY_SEPARATOR . 'actions.txt');
$environments = load_lines($CATEGORIES_DIR . DIRECTORY_SEPARATOR . 'environments.txt');

$style = load_style($CATEGORIES_DIR . DIRECTORY_SEPARATOR . 'style.txt');

$pools = [
  'intro' => load_lines($APP_DIR . DIRECTORY_SEPARATOR . 'intro_pool.txt'),
  'usage' => load_lines($APP_DIR . DIRECTORY_SEPARATOR . 'usage_pool.txt'),
  'ease' => load_lines($APP_DIR . DIRECTORY_SEPARATOR . 'ease_pool.txt'),
  'benefit' => load_lines($APP_DIR . DIRECTORY_SEPARATOR . 'benefit_pool.txt'),
];

$missing = [];
if (empty($characters)) $missing[] = 'characters';
if (empty($actions)) $missing[] = 'actions';
if (empty($environments)) $missing[] = 'environments';
foreach (['intro','usage','ease','benefit'] as $k) if (empty($pools[$k])) $missing[] = 'pool_' . $k;
if ($style === '') $missing[] = 'style';

if (!empty($missing)) json_out(['ok' => false, 'error' => 'missing_inputs', 'missing' => $missing], 500);

$items = [];
$errors = [];
$attempts = [];
$new_images = [];

$json_path = category_json_path($CATEGORIES_DIR, $category);
$existing_ids = [];
if (!$dry) {
  $data_existing = read_category_json_file($json_path);
  foreach ($data_existing['pages'] as $p) {
    if (is_array($p) && isset($p['id'])) $existing_ids[(string)$p['id']] = true;
  }
}

for ($i = 0; $i < $count; $i++) {
  $parts = [
    'character' => $characters[array_rand($characters)],
    'action' => $actions[array_rand($actions)],
    'environment' => $environments[array_rand($environments)],
  ];

  $id = build_id($parts);
  $title = build_title($parts);
  $description = build_description($parts, $pools);
  $prompt = build_prompt($parts, $style);

  if (!$dry && isset($existing_ids[$id])) {
    $attempts[] = [
      'id' => $id,
      'title' => $title,
      'description' => $description,
      'skipped' => 'duplicate_id_in_json',
    ];
    continue;
  }

  // Keep a record of what we tried, even if we skip creating the page
  $attempts[] = [
    'id' => $id,
    'title' => $title,
    'description' => $description,
  ];

  $page_ok = true;

  if ($do_img) {
    if ($api_key === '') {
      $errors[] = ['id' => $id, 'error' => 'missing_api_key'];
      $page_ok = false;
    } else {
      $img_name = sanitize_filename($id) . '.png';
      $out_path = $CATEGORIES_DIR . DIRECTORY_SEPARATOR . $category . DIRECTORY_SEPARATOR . $img_name;

      $has_existing = $skip_existing_img && is_file($out_path) && filesize($out_path) > 0;
      if (!$has_existing) {
        $img_res = gemini_generate_image($api_key, $prompt, $out_path, $aspect_ratio);
        if (($img_res['ok'] ?? false)) $new_images[$id] = $out_path;
        if (!($img_res['ok'] ?? false)) {
          $errors[] = ['id' => $id, 'error' => $img_res];
          $page_ok = false;
          if (is_file($out_path)) @unlink($out_path);
        }
      }

      if ($page_ok) {
        $info = @getimagesize($out_path);
        if (!is_array($info) || (($info['mime'] ?? '') !== 'image/png')) {
          $errors[] = ['id' => $id, 'error' => 'invalid_png_output'];
          $page_ok = false;
          if (is_file($out_path)) @unlink($out_path);
        }
      }

      if ($page_ok) {
        $conv = convert_png_to_1bit_gd($out_path, $ONEBIT_THRESHOLD);
        if (!($conv['ok'] ?? false)) {
          $errors[] = ['id' => $id, 'error' => ['onebit' => $conv]];
        }
      }
    }
  }

  // Only create the page entry if image generation succeeded (or an existing image was already present)
  if ($page_ok) {
    $items[] = [
      'id' => $id,
      'title' => $title,
      'description' => $description,
    ];
    if (!$dry) $existing_ids[$id] = true;
  }
}

$write_result = null;
if (!$dry) {
  $write_result = prepend_unique_pages($json_path, $items);
  if (!($write_result['ok'] ?? false)) {
    json_out(['ok' => false, 'error' => 'write_failed', 'detail' => $write_result], 500);
  }

  if ($do_img && !empty($new_images)) {
    $added_ids = [];
    if (isset($write_result['added_ids']) && is_array($write_result['added_ids'])) {
      foreach ($write_result['added_ids'] as $aid) $added_ids[(string)$aid] = true;
    }

    foreach ($new_images as $nid => $npath) {
      if (!isset($added_ids[(string)$nid])) {
        if (is_file($npath)) @unlink($npath);
      }
    }
  }
}

json_out([
  'ok' => true,
  'category' => $category,
  'count_requested' => $count,
  'count_attempted' => count($attempts),
  'count_generated' => count($items),
  'dry' => $dry,
  'write_result' => $write_result,
  'items' => $items,
  'attempts' => $attempts,
  'errors' => $errors
]);